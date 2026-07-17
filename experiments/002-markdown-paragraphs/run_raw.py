"""A/B test: synthesize a small subset as RAW markdown vs the CLEANED spoken form.

Answers "what does skipping the strip actually sound like?" — how Kokoro vocalizes `#`,
`**`, `[text](url)`, `- `. Uses a handful of syntax-rich units so it's a short Modal call.

Usage: uv run python run_raw.py
"""

import base64
from pathlib import Path

import modal

from pipeline import pipeline

HERE = Path(__file__).parent
FIXTURE = HERE / "fixtures" / "my-ai-adoption-journey.html"
OUT = HERE / "out"
VOICE = "af_heart"

# heading (#), heading (##), a link, and a run-in-bold list item — the syntax-rich cases
INDICES = [0, 1, 11, 24]


def synth(paragraphs: list[str], name: str) -> None:
    kokoro = modal.Cls.from_name("nagara-tts", "Kokoro")
    result = kokoro().synthesize.remote(paragraphs=paragraphs, voice=VOICE)
    ext = "ogg" if result["format"] == "audio/ogg" else "wav"
    dest = OUT / f"{name}.{ext}"
    dest.write_bytes(base64.b64decode(result["audio_base64"]))
    print(f"wrote {dest.name}  ({result['duration']:.1f}s)")


def main() -> None:
    display, spoken, _ = pipeline(FIXTURE.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)

    raw = [display[i] for i in INDICES]
    clean = [spoken[i] for i in INDICES]

    print("=== subset being synthesized ===")
    for i, r, c in zip(INDICES, raw, clean):
        print(f"[{i}] RAW  : {r[:75]!r}")
        print(f"     CLEAN: {c[:75]!r}")

    synth(raw, "audio_raw_subset")
    synth(clean, "audio_clean_subset")


if __name__ == "__main__":
    main()
