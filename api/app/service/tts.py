import random
from typing import Protocol

import modal

from ..config import settings
from ..models.item import ItemStatus
from ..schemas.tts import SynthesisResult

# Curated Kokoro (American-English) voices for the random default; low-grade voices
# are excluded so an un-voiced item always sounds good. Any voice remains explicitly
# requestable — this pool only governs the fallback when none is given.
VOICE_POOL = [
    "af_heart", "af_bella", "af_sarah", "af_sky", "af_aoede", "af_alloy", "af_nova",
    "am_fenrir", "am_michael", "am_puck",
]


def pick_voice() -> str:
    return random.choice(VOICE_POOL)


def spawn_synthesis(paragraphs: list[str], voice: str) -> str:
    """Kick off eager generation on Modal; return the FunctionCall id to persist."""
    kokoro = modal.Cls.from_name(settings.modal_app, settings.modal_cls)
    call = kokoro().synthesize.spawn(paragraphs=paragraphs, voice=voice)
    return call.object_id


def poll_synthesis(call_id: str) -> tuple[ItemStatus, SynthesisResult | str | None]:
    """Lazily resolve a spawned job. Returns one of:
    (ItemStatus.READY, SynthesisResult) | (ItemStatus.GENERATING, None) | (ItemStatus.FAILED, error_str).

    The running-vs-crashed distinction is load-bearing: a still-running job raises
    TimeoutError on get(timeout=0), while a crashed remote job re-raises its exception
    here — so a running job is never misclassified as failed.
    """
    fc = modal.FunctionCall.from_id(call_id)
    try:
        result = fc.get(timeout=0)
    except TimeoutError:
        return ItemStatus.GENERATING, None
    except Exception as e:
        return ItemStatus.FAILED, f"{type(e).__name__}: {e}"

    return ItemStatus.READY, SynthesisResult.model_validate(result)


class Synthesizer(Protocol):
    """Render spoken paragraphs to audio on a remote host with no broker: ``spawn`` returns a
    handle to persist, ``resolve`` reads it lazily on poll. The API never imports the TTS code
    (invariant 5) — a Synthesizer only spawns and resolves it remotely."""

    def spawn(self, paragraphs: list[str], voice: str) -> str: ...

    def resolve(self, call_id: str) -> tuple[ItemStatus, SynthesisResult | str | None]: ...


class ModalSynthesizer:
    """The Modal-backed ``Synthesizer``: spawn through the class handle, resolve with a
    non-blocking get whose exception type tells a running job from a crashed one. Both calls are
    synchronous Modal-client calls, bridged through the threadpool at the step."""

    def spawn(self, paragraphs: list[str], voice: str) -> str:
        return spawn_synthesis(paragraphs, voice)

    def resolve(self, call_id: str) -> tuple[ItemStatus, SynthesisResult | str | None]:
        return poll_synthesis(call_id)
