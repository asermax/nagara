---
title: "Formulas read aloud"
tags:
  - adventure
summary: "Build the formula path: recover the LaTeX the extractor discards, speak it, and describe the display ones."
status: open
kind: raid
priority: 1-now
created: "2026-08-30"
---

# Formulas read aloud

## Destination

Every formula an article carries reaches a listener as speech and a client as raw LaTeX. No formula is silent, and none is read aloud as syntax. Reaching the end means the five measured families all pass through: MathML inline, MathML display, `$$…$$` inside a bare `<div>`, and the two raw-delimiter leaks; each with a fixture, and each played once before its slice is called done.

This raid has no journey behind it. Its ground was cleared by one loose design quest, [[latex-formulas-not-read]], which descends to the module, the types and the signatures. **Every decision here lives on that quest and nothing was copied across**: the carrier codepoints, the outermost-wrapper rule, the position-decides-voicing argument, the floor ladder, and the raw-LaTeX forward commitment are all settled there, with the measurements that settled them.

## Bearings

**The ground.** `api/app/service/` (a new `formulas.py`, plus `extract.py`, `describe.py`, and `images.py`'s anchor probe) and `api/app/schemas/items.py`. Recovery goes at the single `trafilatura.extract` seam inside `_extract_units_from_html`, so the plain fetch and the firecrawl fallback both get it and invariant 1 holds by construction. `tts/` is untouched: it receives a list of spoken strings and that contract does not change. `web/` does not exist and is not built here.

**Read first.** [[latex-formulas-not-read]] in full; it is the whole design and it is long. Then `api/app/service/extract.py` (`_extract_units_from_html`, `units_from_markdown`, `_split_units`, `_normalize_display`, `_to_spoken`, `sanitize_spoken`), `api/app/service/describe.py` (`enrich_with_descriptions`, the shared budget, the floor, the code-raises rule), `api/app/schemas/items.py` (the two discriminated unions), and the notes [[article-extraction]], [[item-contract]], [[the-describer]].

**Standing preferences.**

- **Recovery rewrites, it never re-extracts.** `carry_math` hands its output to `trafilatura.extract` and to nothing else. `extract_article` keeps returning the original `page.html`, because `images.py` probes that tree and `extract_metadata` reads it for the title.
- **Replace the outermost math wrapper, never the `<math>` node.** Measured: replacing the node recovers 0 of 99 formulas on Wikipedia, because MediaWiki hides the MathML in an a11y wrapper trafilatura discards along with anything placed inside it.
- **A formula never fails the item and is never dropped.** It degrades down the floor ladder and the last rung is a real spoken form carrying the actual content. This is the one place the formula path parts from the code path it otherwise mirrors, and it is deliberate.
- **The notes are the raid's ending, not a slice's homework.** The design names three; add [[the-describer]], because a third describe kind with a different failure rule is exactly what that note documents. All four are written once, at the end, out of every solved quest at once, per [[quest-log/README|the quest log]].
- **A fixture per family, on the slice that covers the family.** Three land on the first slice and three on the third. An extraction rule with no fixture is a rule nobody can re-check, so a slice carrying one is not done.
- **Listen to it.** One recovered display formula and one inline formula are played before any slice is called done. A carrier that survives into `spoken` reads as "left white square bracket i colon", and no test summary and no diff will ever show you that.

**Negative bearings.** A sibling session is working `code-blocks-dropped-before-extraction` in its own worktree (named, not linked: it belongs to another effort and a link into it dangles the moment that effort is struck), in `api/`: expect `extract.py` to have moved under you, and rebase rather than assume. Do not reach for a LaTeX-to-speech library; `latex2speech`, `mathspeak`, `speech-rule-engine` and `mathml2speech` are all absent from PyPI and `pylatexenc` produces unicode Kokoro cannot read, which is why the rules table is hand-rolled. Do not add a formula equivalent of the code path's "every one failed" raise.

## Trials

**None, and that is the point.** The design quest descends to types, signatures and call sites, and the read-through at the muster turned up gaps and two mislocated hazards rather than anything unstatable. Each gap is written on the slice that answers it. If a trial appears mid-build, the ground was not clear after all and it belongs back in a journey rather than being guessed at.

## Solved

- [[latex-formulas-not-read]] — settled the whole shape, down to the module, the types, the signatures and the call sites: recovery at the one extraction seam via a text carrier, a fourth `FormulaUnit`, raw LaTeX in `display`, inline math verbalized in place by rules and display math described on the existing budget with the verbalized LaTeX as its floor. Fixes every part of the shape this raid builds. It left behind four real articles fetched and pushed through the live pipeline, and two carrier choices settled by measurement rather than taste. **It was a loose design quest and was adopted into this raid at the muster**, because the raid links into it and nothing outside an effort may link into one: as an effort of one it would have been struck on landing and dangled every link here. It is struck with this raid, not before.

One line lands here per slice as it solves: what it built, which part of the shape that fixes, and what it left behind for the next session to go and look at.

## Out of scope

**Formulas rendered to images with no MathML twin and no usable alt** (some Substack and Medium posts). No LaTeX exists in the page to recover, and the image path already gives them a described `ImageUnit`, which is the right fallback.

**A page rendering bare `$…$` while declaring no math renderer.** It keeps leaking. Nothing distinguishes it from "between $5 and $10 million", and the design accepts that residual rather than chasing it.

**The KaTeX renderer in `web/`.** Raw LaTeX in `display` is a forward commitment this raid makes on behalf of a client nobody has written. Honouring it belongs to whichever adventure builds `web/`.

**Replacing the verbalizer with a library.** There is nothing on PyPI to replace it with. A library appearing later is one of the things that would make this shape stop being true, and it is recorded as such on the design quest.

---

Related: [[quest-log/README|the quest log]] · [[latex-formulas-not-read]]
