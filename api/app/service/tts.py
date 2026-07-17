import modal

from ..config import settings
from ..schemas.tts import SynthesisResult


def spawn_synthesis(paragraphs: list[str], voice: str) -> str:
    """Kick off eager generation on Modal; return the FunctionCall id to persist."""
    kokoro = modal.Cls.from_name(settings.modal_app, settings.modal_cls)
    call = kokoro().synthesize.spawn(paragraphs=paragraphs, voice=voice)
    return call.object_id


def poll_synthesis(call_id: str) -> tuple[str, SynthesisResult | str | None]:
    """Lazily resolve a spawned job. Returns one of:
    ('ready', SynthesisResult) | ('generating', None) | ('failed', error_str).

    The running-vs-crashed distinction is load-bearing: a still-running job raises
    TimeoutError on get(timeout=0), while a crashed remote job re-raises its exception
    here — so a running job is never misclassified as failed.
    """
    fc = modal.FunctionCall.from_id(call_id)
    try:
        result = fc.get(timeout=0)
    except TimeoutError:
        return "generating", None
    except Exception as e:
        return "failed", f"{type(e).__name__}: {e}"

    return "ready", SynthesisResult.model_validate(result)
