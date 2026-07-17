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

    The not-ready-vs-raised distinction is the load-bearing probe (experiment 001, task #2):
    a still-running job raises TimeoutError on get(timeout=0); a Modal-side crash re-raises
    the remote exception here.
    """
    fc = modal.FunctionCall.from_id(call_id)
    try:
        result = fc.get(timeout=0)
    except TimeoutError:
        return "generating", None
    except Exception as e:
        return "failed", f"{type(e).__name__}: {e}"

    return "ready", SynthesisResult.model_validate(result)
