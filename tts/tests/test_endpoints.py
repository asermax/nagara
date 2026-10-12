import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import modal
import numpy as np
import pytest
from fastapi.testclient import TestClient

import app
from app import SR, synthesize_to, web_app

PARAGRAPHS = ["First paragraph.", "Second paragraph,\nwith a second line.", "Third."]


def stub_pipeline(text: str, voice: str) -> Iterator[tuple[str, str, np.ndarray]]:
    for line in text.split("\n"):
        yield line, line, np.full(int(SR * 0.05 * len(line)), 0.1, dtype=np.float32)


class Destination:
    def __init__(self, status: int) -> None:
        self.status = status
        self.requests: list[dict] = []

        destination = self

        class Handler(BaseHTTPRequestHandler):
            def do_PUT(self) -> None:
                body = self.rfile.read(int(self.headers["content-length"]))
                destination.requests.append(
                    {"path": self.path, "content_type": self.headers["content-type"], "body": body}
                )
                self.send_response(destination.status)
                self.send_header("content-length", "0")
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = (
            f"http://127.0.0.1:{self.server.server_port}/audio/itm_0000abcd.ogg?X-Amz-Signature=x"
        )

        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def destination(request: pytest.FixtureRequest) -> Iterator[Destination]:
    server = Destination(getattr(request, "param", 200))
    yield server
    server.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(web_app)


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    calls: list[tuple] = []

    async def spawn(*args: object) -> SimpleNamespace:
        calls.append(args)
        return SimpleNamespace(object_id="fc-01K7SPAWNED")

    monkeypatch.setattr(
        app,
        "Kokoro",
        lambda: SimpleNamespace(synthesize=SimpleNamespace(spawn=SimpleNamespace(aio=spawn))),
    )

    return calls


def call_answering(monkeypatch: pytest.MonkeyPatch, outcome: object) -> list[str]:
    looked_up: list[str] = []

    async def get(timeout: float) -> object:
        assert timeout == 0

        if isinstance(outcome, BaseException):
            raise outcome

        return outcome

    def from_id(call_id: str) -> SimpleNamespace:
        looked_up.append(call_id)
        return SimpleNamespace(get=SimpleNamespace(aio=get))

    monkeypatch.setattr(modal.FunctionCall, "from_id", from_id)

    return looked_up


def test_start_spawns_the_synthesis_with_every_field_and_answers_its_call_id(
    client: TestClient, spawned: list[tuple]
) -> None:
    response = client.post(
        "/start",
        json={
            "paragraphs": PARAGRAPHS,
            "voice": "bm_george",
            "destination": "https://put.example/a",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"call_id": "fc-01K7SPAWNED"}
    assert spawned == [(PARAGRAPHS, "bm_george", "https://put.example/a")]


def test_start_without_a_voice_synthesizes_with_af_heart(
    client: TestClient, spawned: list[tuple]
) -> None:
    response = client.post(
        "/start", json={"paragraphs": PARAGRAPHS, "destination": "https://put.example/a"}
    )

    assert response.status_code == 200
    assert spawned == [(PARAGRAPHS, "af_heart", "https://put.example/a")]


def test_start_without_a_destination_is_rejected_before_anything_is_spawned(
    client: TestClient, spawned: list[tuple]
) -> None:
    response = client.post("/start", json={"paragraphs": PARAGRAPHS, "voice": "af_heart"})

    assert response.status_code == 422
    assert spawned == []


def test_synthesis_uploads_the_audio_with_its_content_type_and_returns_timing_only(
    destination: Destination,
) -> None:
    result = synthesize_to(stub_pipeline, PARAGRAPHS, "af_heart", destination.url)

    assert len(destination.requests) == 1
    upload = destination.requests[0]
    assert upload["path"] == "/audio/itm_0000abcd.ogg?X-Amz-Signature=x"
    assert upload["content_type"] == result.format
    assert upload["body"].startswith(b"OggS" if result.format == "audio/ogg" else b"RIFF")

    assert set(result.model_dump()) == {"format", "duration", "timings"}
    assert len(result.timings) == len(PARAGRAPHS)
    assert result.timings[-1].end == pytest.approx(result.duration)


@pytest.mark.parametrize("destination", [403], indirect=True)
def test_synthesis_fails_when_the_destination_refuses_the_upload(destination: Destination) -> None:
    with pytest.raises(Exception, match="403"):
        synthesize_to(stub_pipeline, PARAGRAPHS, "af_heart", destination.url)

    assert len(destination.requests) == 1


def test_result_of_a_running_call_is_202(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    looked_up = call_answering(monkeypatch, TimeoutError())

    response = client.get("/result", params={"call_id": "fc-01K7RUNNING"})

    assert response.status_code == 202
    assert response.json() == {"status": "running"}
    assert looked_up == ["fc-01K7RUNNING"]


def test_result_of_a_finished_call_is_its_contiguous_timing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, destination: Destination
) -> None:
    output = synthesize_to(stub_pipeline, PARAGRAPHS, "af_heart", destination.url).model_dump()
    call_answering(monkeypatch, output)

    response = client.get("/result", params={"call_id": "fc-01K7DONE"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"format", "duration", "timings"}
    assert body["format"] in ("audio/ogg", "audio/wav")

    timings = body["timings"]
    assert len(timings) == len(PARAGRAPHS)
    assert timings[0]["start"] == 0.0

    for previous, following in zip(timings, timings[1:]):
        assert following["start"] == previous["end"]

    assert timings[-1]["end"] == pytest.approx(body["duration"])


@pytest.mark.parametrize(
    "raised",
    [
        RuntimeError("Client error '403 Forbidden'"),
        modal.exception.FunctionTimeoutError("timed out"),
    ],
)
def test_result_of_a_call_whose_synthesis_raised_is_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, raised: BaseException
) -> None:
    call_answering(monkeypatch, raised)

    response = client.get("/result", params={"call_id": "fc-01K7RAISED"})

    assert response.status_code == 500
    assert response.json() == {"error": str(raised)}


def test_result_of_a_call_modal_no_longer_holds_is_410(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_answering(monkeypatch, modal.exception.OutputExpiredError())

    response = client.get("/result", params={"call_id": "fc-01K7EXPIRED"})

    assert response.status_code == 410


def test_result_of_a_call_id_modal_never_issued_is_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_answering(monkeypatch, modal.exception.NotFoundError("No Function Call with ID found."))

    response = client.get("/result", params={"call_id": "fc-01K7UNKNOWN"})

    assert response.status_code == 422


@pytest.mark.parametrize("call_id", ["garbage", "in-01K7NOTACALL", ""])
def test_result_of_something_that_is_not_a_call_id_is_422_without_asking_modal(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, call_id: str
) -> None:
    looked_up = call_answering(monkeypatch, TimeoutError())

    response = client.get("/result", params={"call_id": call_id})

    assert response.status_code == 422
    assert looked_up == []
