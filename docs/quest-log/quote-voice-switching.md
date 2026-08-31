---
title: "Quote voice switching"
tags:
  - quest
summary: "Detect quoted passages and switch the Kokoro voice for them, the way an audiobook narrator differentiates dialogue."
status: open
kind: spike
adventure:
blocked_by: []
priority: 2-soon
created: "2026-07-17"
---

# Quote voice switching

## What

Detect quoted passages in an article and switch the Kokoro voice for them, the way an audiobook narrator differentiates dialogue from narration: a listener hears a quote as a distinct voice rather than the narrator reading it flat.

Not yet enumerated as something a single probe could clear. Candidates already named: how good attribution and nesting detection can be made without over-triggering on ordinary emphasis or a blockquote that isn't dialogue; whether the read-along highlight should signal the voice switch visually as well as audibly.

> [!warning] The premise that blockquotes arrive identifiable does not hold
> A blockquote reaches nagara as an ordinary paragraph, indistinguishable from the surrounding prose in both `display` and `spoken`, so there is nothing to detect and nothing to switch voice on. trafilatura recognises the element — its XML output carries `<quote>` — and then its markdown writer drops it: `replace_element_text` in `trafilatura/xml.py` branches on `head`, `del`, `hi`, `code`, `ref` and `cell`, and has no `quote` branch. The text survives and is read aloud; only the quote-ness is lost.
>
> The corollary is that `_split_units`' `_BLOCKQUOTE` branch in `api/app/service/extract.py` is dead code. Confirmed on real data rather than on the probe alone: zero markdown blockquote lines across all four `api/tests/fixtures/*.html` plus a live article, including `t17_newyorker.html`, which carries a real `<blockquote>` in its source.
>
> So this quest has a precondition its `## What` does not state: quote-ness has to be restored at the extraction seam before voice switching has any input at all. Measured 2026-08-30 in the missing-quotes-and-code-blocks spike, and upstream-version-sensitive — it stops being true if trafilatura adds a `quote` branch to its markdown writer. The evidence is `git show 26f42ee:docs/quest-log/missing-quotes-and-code-blocks.md`, and `spike/quote_marker.py` on the tag `spike/missing-quotes-and-code-blocks`.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[queue]]
