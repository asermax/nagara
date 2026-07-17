"""One-time: fetch the real article HTML into fixtures/ so every run is offline.

Usage: uv run python snapshot.py
"""

from pathlib import Path

import trafilatura

URL = "https://mitchellh.com/writing/my-ai-adoption-journey"
DEST = Path(__file__).parent / "fixtures" / "my-ai-adoption-journey.html"


def main() -> None:
    response = trafilatura.fetch_response(URL, decode=True, with_headers=True)
    if response is None or not response.html:
        raise SystemExit("fetch failed")

    DEST.parent.mkdir(exist_ok=True)
    DEST.write_text(response.html, encoding="utf-8")
    print(f"saved {len(response.html)} chars → {DEST}")


if __name__ == "__main__":
    main()
