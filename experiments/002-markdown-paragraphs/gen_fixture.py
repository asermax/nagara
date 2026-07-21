"""Generate a rich real fixture for the 003 player spike: fetch → pipeline → Modal TTS →
write {slug}.json (index,start,end,display) + audio into the spike.

Usage: uv run python gen_fixture.py <url> <slug>
"""

import base64
import json
import sys
from pathlib import Path

import modal
import trafilatura

from pipeline import pipeline

VOICE = "af_heart"
SPIKE = Path(__file__).parent.parent / "003-read-along-player" / "spike"


def ext_for(fmt: str) -> str:
    if "ogg" in fmt or "opus" in fmt:
        return "ogg"
    if "wav" in fmt:
        return "wav"
    return fmt.rsplit("/", 1)[-1]


def main() -> None:
    url, slug = sys.argv[1], sys.argv[2]

    resp = trafilatura.fetch_response(url, decode=True, with_headers=True)
    if resp is None or not resp.html:
        raise SystemExit("fetch failed")

    display, spoken, dropped = pipeline(resp.html)
    print(f"pipeline: {len(display)} units, dropped(empty)={len(dropped)}")

    kokoro = modal.Cls.from_name("nagara-tts", "Kokoro")
    result = kokoro().synthesize.remote(paragraphs=spoken, voice=VOICE)
    timeline = result["paragraphs"]
    assert len(timeline) == len(display), f"timeline {len(timeline)} != display {len(display)}"

    paragraphs = [
        {"index": p["index"], "start": p["start"], "end": p["end"], "display": display[p["index"]]}
        for p in timeline
    ]
    item = {"id": slug, "title": display[0].lstrip("# ").strip(), "duration": result["duration"], "paragraphs": paragraphs}

    ext = ext_for(result["format"])
    (SPIKE / "src" / "fixtures" / f"{slug}.json").write_text(json.dumps(item, ensure_ascii=False, indent=0), encoding="utf-8")
    (SPIKE / "public" / f"{slug}.{ext}").write_bytes(base64.b64decode(result["audio_base64"]))
    print(f"wrote {slug}.json ({len(paragraphs)} units) + {slug}.{ext} ({result['duration']:.1f}s, {result['format']})")


if __name__ == "__main__":
    main()
