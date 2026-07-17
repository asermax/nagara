from unittest.mock import MagicMock, patch

from app.schemas.tts import SynthesisResult
from app.service.tts import poll_synthesis, spawn_synthesis


@patch("app.service.tts.modal")
def test_spawn_returns_call_id(mock_modal):
    call = MagicMock(object_id="fc-123")
    mock_modal.Cls.from_name.return_value.return_value.synthesize.spawn.return_value = call

    assert spawn_synthesis(["a", "b"], "af_heart") == "fc-123"


@patch("app.service.tts.modal")
def test_poll_ready_returns_parsed_result(mock_modal):
    mock_modal.FunctionCall.from_id.return_value.get.return_value = {
        "audio_base64": "AAA=",
        "format": "audio/ogg",
        "sample_rate": 24000,
        "duration": 2.0,
        "paragraphs": [{"index": 0, "start": 0.0, "end": 2.0, "text": "hi"}],
    }

    status, result = poll_synthesis("fc-1")

    assert status == "ready"
    assert isinstance(result, SynthesisResult)
    assert result.duration == 2.0
    assert result.paragraphs[0].text == "hi"


@patch("app.service.tts.modal")
def test_poll_generating_on_timeout(mock_modal):
    mock_modal.FunctionCall.from_id.return_value.get.side_effect = TimeoutError()

    status, payload = poll_synthesis("fc-1")

    assert status == "generating"
    assert payload is None


@patch("app.service.tts.modal")
def test_poll_failed_on_remote_raise(mock_modal):
    mock_modal.FunctionCall.from_id.return_value.get.side_effect = RuntimeError("forced failure")

    status, payload = poll_synthesis("fc-1")

    assert status == "failed"
    assert "forced failure" in payload
