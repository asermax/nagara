"""End-to-end round-trip: fixture → display[]/spoken[] → deployed TTS → zip by index.

Writes out/{display.md, spoken.txt, timeline.json, audio.*} for inspection + the listen.
The TTS is the already-deployed nagara-tts Modal service, called synchronously (.remote()) —
the spike runs once and just needs audio + the index-keyed timeline back.

Usage:
  uv run python run.py --preflight   # trivial call, confirm the deployment is alive
  uv run python run.py               # full real-fixture round-trip
"""

import base64
import json
import sys
from pathlib import Path

import modal

from pipeline import pipeline

HERE = Path(__file__).parent
FIXTURE = HERE / "fixtures" / "my-ai-adoption-journey.html"
OUT = HERE / "out"
VOICE = "af_heart"


def synthesize(spoken: list[str]) -> dict:
    kokoro = modal.Cls.from_name("nagara-tts", "Kokoro")
    return kokoro().synthesize.remote(paragraphs=spoken, voice=VOICE)


def check_timing(timeline: list[dict], duration: float) -> None:
    prev = 0.0
    for e in timeline:
        assert e["start"] <= e["end"], f"unit {e['index']}: start>end"
        assert abs(e["start"] - prev) < 1e-6, f"unit {e['index']}: gap/overlap at {e['start']} vs {prev}"
        prev = e["end"]
    assert abs(prev - duration) < 1e-3, f"last end {prev} != duration {duration}"
    print(f"timing OK: {len(timeline)} contiguous windows, last end == duration ({duration:.2f}s)")


def main() -> None:
    if "--preflight" in sys.argv:
        result = synthesize(["Hello.", "This is a preflight check."])
        print(f"preflight OK: {result['format']}, {result['duration']:.2f}s, "
              f"{len(result['paragraphs'])} windows")
        return

    display, spoken, dropped = pipeline(FIXTURE.read_text(encoding="utf-8"))
    print(f"pipeline: {len(display)} units, aligned={len(display) == len(spoken)}, "
          f"dropped(empty spoken)={len(dropped)}")

    result = synthesize(spoken)
    timeline = result["paragraphs"]
    assert len(timeline) == len(display), f"timeline {len(timeline)} != display {len(display)}"

    check_timing(timeline, result["duration"])

    OUT.mkdir(exist_ok=True)
    (OUT / "display.md").write_text("\n\n".join(display), encoding="utf-8")
    (OUT / "spoken.txt").write_text("\n\n".join(spoken), encoding="utf-8")
    zipped = [
        {"index": e["index"], "start": e["start"], "end": e["end"],
         "display": display[e["index"]], "spoken": spoken[e["index"]]}
        for e in timeline
    ]
    (OUT / "timeline.json").write_text(json.dumps(zipped, indent=2), encoding="utf-8")

    ext = "ogg" if result["format"] == "audio/ogg" else "wav"
    (OUT / f"audio.{ext}").write_bytes(base64.b64decode(result["audio_base64"]))
    print(f"wrote out/display.md, out/spoken.txt, out/timeline.json, out/audio.{ext}")


if __name__ == "__main__":
    main()
