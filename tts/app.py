"""Nagara TTS service — Kokoro-82M on Modal.

Two web endpoints behind Modal's proxy auth: start spawns a synthesis of paragraphs[] that
uploads its encoded audio to a presigned PUT URL, and result answers with the call's
per-paragraph {start, end} timing, duration and format once it is done. Runs as its own
Modal app; the item Workflow reaches it over HTTP.

Serve:   uv run modal serve app.py
Deploy:  uv run modal deploy app.py
"""

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Annotated

import httpx
import modal
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    import numpy as np

app = modal.App("nagara-tts")

SR = 24000
PAUSE_S = 0.1  # inter-paragraph silence — enough to mark the break without stalling the prose
UPLOAD_TIMEOUT_S = 60.0
WEB_DEPS = ("fastapi[standard]", "httpx")


class StartRequest(BaseModel):
    paragraphs: list[str]
    voice: str = "af_heart"
    destination: str


class StartResponse(BaseModel):
    call_id: str


class Timing(BaseModel):
    start: float
    end: float


class SynthesisResult(BaseModel):
    format: str
    duration: float
    timings: list[Timing]


class Running(BaseModel):
    status: str = "running"


class ErrorBody(BaseModel):
    error: str


def build_timeline(durations: list[float], pause_s: float) -> list[dict]:
    """Cumulative per-paragraph windows. The inter-paragraph pause is folded into the
    *preceding* paragraph's end, so windows are contiguous and the last `end` equals the
    total audio duration (sum of durations + (n-1) pauses)."""
    timeline, t, n = [], 0.0, len(durations)
    for i, dur in enumerate(durations):
        end = t + dur + (pause_s if i < n - 1 else 0.0)
        timeline.append({"index": i, "start": t, "end": end})
        t = end
    return timeline


def encode_opus(audio: "np.ndarray") -> tuple[bytes, str]:
    import io
    import subprocess

    import soundfile as sf

    wav = io.BytesIO()
    sf.write(wav, audio, SR, format="WAV")

    try:
        opus = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", "pipe:0",
             "-c:a", "libopus", "-b:a", "24k", "-ac", "1", "-f", "ogg", "pipe:1"],
            input=wav.getvalue(), stdout=subprocess.PIPE, check=True,
        ).stdout
        return opus, "audio/ogg"
    except Exception:
        # WAV fallback if the codec path snags — "playable" is the judged property
        return wav.getvalue(), "audio/wav"


def synthesize_to(
    pipeline: Callable[..., Iterable], paragraphs: list[str], voice: str, destination: str
) -> SynthesisResult:
    import numpy as np

    gap = np.zeros(int(SR * PAUSE_S), dtype=np.float32)

    audios = [np.concatenate([a for _, _, a in pipeline(para, voice=voice)]) for para in paragraphs]
    durations = [len(audio) / SR for audio in audios]

    chunks = []

    for i, audio in enumerate(audios):
        chunks.append(audio)

        if i < len(audios) - 1:
            chunks.append(gap)

    full = np.concatenate(chunks)

    audio_bytes, fmt = encode_opus(full)

    # A refused upload must fail the call, so the result endpoint answers 500 instead of
    # timing for audio that never reached the bucket.
    httpx.put(
        destination,
        content=audio_bytes,
        headers={"content-type": fmt},
        timeout=UPLOAD_TIMEOUT_S,
    ).raise_for_status()

    return SynthesisResult(
        format=fmt,
        duration=len(full) / SR,
        timings=[
            Timing(start=entry["start"], end=entry["end"])
            for entry in build_timeline(durations, PAUSE_S)
        ],
    )


def _bake():
    from kokoro import KPipeline

    list(KPipeline(lang_code="a")("warm up", voice="af_heart"))


image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("espeak-ng", "ffmpeg")
    .pip_install("kokoro==0.9.4", "soundfile", "torch", "numpy")
    .run_function(_bake)
    # After the bake, so adding the web deps does not re-run it; app.py imports them at load.
    .pip_install(*WEB_DEPS)
)

web_image = modal.Image.debian_slim(python_version="3.12").pip_install(*WEB_DEPS)


@app.cls(
    image=image,
    gpu="L4",
    scaledown_window=300,  # stay warm across a session's burst of pushes
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},  # ~27s -> ~6s cold start
)
class Kokoro:
    @modal.enter(snap=True)
    def load(self):
        from kokoro import KPipeline

        self.pipeline = KPipeline(lang_code="a")

    @modal.method()
    def synthesize(self, paragraphs: list[str], voice: str, destination: str) -> dict[str, object]:
        # A plain dict crosses Modal's result store: unpickling the model in the web
        # container would depend on how each container names this module.
        return synthesize_to(self.pipeline, paragraphs, voice, destination).model_dump()


web_app = FastAPI()


def respond(status: int, body: BaseModel) -> JSONResponse:
    return JSONResponse(status_code=status, content=body.model_dump())


@web_app.post("/start")
async def start(body: StartRequest) -> StartResponse:
    call = await Kokoro().synthesize.spawn.aio(body.paragraphs, body.voice, body.destination)

    return StartResponse(call_id=call.object_id)


# Modal only reports a malformed id as a generic ExecutionError, so the prefix is validated
# up front to keep it a 422 rather than a 500.
@web_app.get("/result", response_model=SynthesisResult)
async def result(call_id: Annotated[str, Query(pattern=r"^fc-")]) -> JSONResponse | dict:
    try:
        output = await modal.FunctionCall.from_id(call_id).get.aio(timeout=0)
    except modal.exception.OutputExpiredError:
        return respond(410, ErrorBody(error="result expired"))
    except modal.exception.NotFoundError:
        return respond(422, ErrorBody(error="unknown call id"))
    except TimeoutError:
        # The builtin TimeoutError is get(timeout=0)'s "still running"; Modal's own
        # FunctionTimeoutError is a different class and falls through to 500 below.
        return respond(202, Running())
    except Exception as error:
        return respond(500, ErrorBody(error=str(error)))

    return output


@app.function(image=web_image)
@modal.asgi_app(requires_proxy_auth=True)
def web() -> FastAPI:
    return web_app
