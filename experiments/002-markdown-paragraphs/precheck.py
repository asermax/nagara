"""Cheap richness pre-check: fetch candidate URLs, run the pipeline, count construct
classes in the display units — no Modal. Pick the richest before spending synthesis."""

import re
import sys

import trafilatura

from pipeline import pipeline

CANDIDATES = sys.argv[1:] or [
    "https://newsletter.pragmaticengineer.com/p/revisiting-no-silver-bullets-in-the",
    "https://martinfowler.com/articles/micro-frontends.html",
    "https://jvns.ca/blog/2023/08/16/what-s-a-long-term-support-release/",
    "https://mitchellh.com/writing/non-planar-3d-printing",
]


def classify(units: list[str]) -> dict:
    counts = {"headings": 0, "list_items": 0, "code": 0, "blockquote": 0, "table": 0, "emphasis_or_link": 0}
    for u in units:
        s = u.strip()
        if re.match(r"^#{1,6}\s", s):
            counts["headings"] += 1
        elif re.match(r"^([-*+]|\d+\.)\s", s):
            counts["list_items"] += 1
        elif s.startswith("```") or "```" in s:
            counts["code"] += 1
        elif s.startswith(">"):
            counts["blockquote"] += 1
        elif "|" in s and s.count("|") >= 2:
            counts["table"] += 1
        if "*" in s or "[" in s or "_" in s or "`" in s:
            counts["emphasis_or_link"] += 1
    return counts


def main() -> None:
    for url in CANDIDATES:
        try:
            resp = trafilatura.fetch_response(url, decode=True, with_headers=True)
            if resp is None or not resp.html:
                print(f"FETCH FAIL  {url}")
                continue
            display, spoken, dropped = pipeline(resp.html)
            c = classify(display)
            print(f"\n{url}\n  units={len(display)} dropped={len(dropped)}  {c}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {url}: {e!r}")


if __name__ == "__main__":
    main()
