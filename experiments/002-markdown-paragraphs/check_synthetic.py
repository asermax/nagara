"""Mandatory hostile-construct strip check (criterion 5 + the hostile half of criterion 1).

The real article (mitchellh) contains no fenced code or blockquotes, so this synthetic
snippet — representative of what trafilatura markdown emits — is what actually exercises
disproof #5 (does a fenced code block fragment) and the hostile half of #1 (residual
syntax on constructs the real fixture lacks). Strip-level only; no TTS round-trip.

Usage: uv run python check_synthetic.py
"""

import re
from pathlib import Path

from pipeline import split_units, to_spoken

SNIPPET = (Path(__file__).parent / "fixtures" / "hostile.md").read_text(encoding="utf-8")

_SYNTAX = re.compile(r"\*\*|__|\]\(|`|^#{1,6} |^\s*[-*+] |^\s*\d+\.\s|^\s*>|\*", re.M)


def main() -> None:
    units = split_units(SNIPPET)
    print(f"=== {len(units)} display units ===")
    for i, u in enumerate(units):
        said = to_spoken(u)
        fenced = u.lstrip().startswith("```")
        lines_in_unit = u.count("\n") + 1
        flag = "  <-- CODE (atomic)" if fenced else ""
        print(f"[{i}] display ({lines_in_unit} src line(s)){flag}: {u[:70]!r}")
        print(f"     spoken: {said[:70]!r}")

    print()
    spoken = [to_spoken(u) for u in units]

    # criterion 5a: the code block is ONE unit, not fragmented per line
    code_units = [u for u in units if u.lstrip().startswith("```")]
    fragmented = any(re.match(r"^\s*(def |return |total )", u) for u in units)
    print("code block is a single atomic unit:", len(code_units) == 1 and not fragmented)

    # criterion 1 (hostile): no residual markdown syntax in any spoken unit
    dirty = [(i, s) for i, s in enumerate(spoken) if _SYNTAX.search(s)]
    print("spoken units with residual syntax:", len(dirty))
    for i, s in dirty:
        print("   DIRTY", i, repr(s))


if __name__ == "__main__":
    main()
