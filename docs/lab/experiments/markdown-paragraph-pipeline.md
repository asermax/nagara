---
title: "Markdown paragraph pipeline"
tags:
  - experiment
summary: "Can a paragraph carry markdown to the render layer while Kokoro's audio stays clean and the timing stays exact? Yes: a single markdown extraction with a derived, index-keyed spoken form needs no TTS contract change; the real risks were segmentation and the strip, not the HTML→markdown boundary."
status: cleared
started: 2026-07-17
concluded: 2026-07-17
branch:
ideas:
  - "[[markdown-formatted-paragraphs]]"
---

# Markdown paragraph pipeline

Serves [[markdown-formatted-paragraphs]], showing a paragraph with its real formatting while the audio stays clean prose and the highlight stays exactly on what is read. Ran as an isolated, throwaway sandbox at `experiments/002-markdown-paragraphs/` (a deliberate deviation from the project's graduate-in-place convention at the time, since this is a narrow mechanism probe that does not need the API/DB/Modal-spawn machinery); there is no idea branch to point `branch` at.

This is a pipeline-**integrity** question. Whether the formatting is faithfully extracted, and whether it is ultimately worth the added complexity, were treated as givens and parked as open unknowns; see [[markdown-formatted-paragraphs]] and [[markdown-faithfulness-and-worth-it]].

## Unknowns it clears

- Can spoken text be stripped clean of markdown syntax generally, without per-article special-casing?
- Does any construct force display and spoken apart so the 1:1 index breaks (the single-segmentation claim)?
- Does carrying markdown regress the read-along timing invariants proven in [[player-ready-item]]?
- Does the TTS contract need to change to carry markdown?

## Experiment

A single markdown extraction is the one source of truth, with spoken text *derived* from it, so display and audio share one segmentation and one index, and alignment is structural rather than reconciled. Concretely: `trafilatura.extract(output_format="markdown", include_formatting, include_links, include_tables=False)` yields `display[]`; a small markdown-it-py-based renderer produces `spoken[]` (same length, same index, syntax stripped, links reduced to anchor text); `spoken[]` goes to the already-deployed, unchanged TTS service, which already returns timing keyed by list position; the timing is zipped onto both arrays by index.

Everything the judging does not test is hardcoded: one real reading-list article (Mitchell Hashimoto's "My AI Adoption Journey", the clean-HTML fixture from [[player-ready-item]]), one voice, no database, no API server. A mandatory synthetic snippet containing a fenced code block, a blockquote, and an inline link is run through the strip regardless of what the real article contains, because a fixture that happens not to carry a hazardous construct cannot be used to refute a claim about it (see [[lab/README|the lab]]'s "pre-register a synthetic probe" method note). Tables are out of scope this run (`include_tables=False`), matching the pipeline at the time.

## Acceptance criteria

Pre-registered 2026-07-17 before any of it was built; the numbered conditions below are the original disproof list, unedited. Disproven if any of:

1. **Strip isn't general**: `spoken[]` cannot be made syntax-free (residual `* _ # [ ] (url)` `` ` `` `> |`) or links leak their URL, without per-article or per-construct special-casing beyond a small general renderer;
2. **Alignment-free promise fails**: some construct forces a split or merge that breaks the 1:1 between `display[i]`, `spoken[i]`, and the timeline;
3. **Timing breaks**: the timeline over the markdown-derived `spoken[]` is non-monotonic, overlapping, or its last `end` no longer matches the audio duration;
4. **Audio dirties**: playback vocalizes markdown syntax or reads unnaturally;
5. **Code blocks fragment**: a fenced code block shatters into per-line degenerate mini-units that cannot be re-merged cleanly.

Task criteria: every `spoken[i]` is free of markdown syntax and every link reduces to its anchor text; `len(display) == len(spoken) == len(timeline)` with index `i` referring to the same logical unit in all three; the returned timeline is monotonic, non-overlapping, contiguous, with last `end` ≈ audio duration; on listen, no markdown syntax is spoken; against the synthetic snippet, a fenced code block merges into one atomic unit and a blockquote strips to clean spoken prose (strip-level only: the timing and audio round-trip for these two constructs is explicitly not tested this run).

## Findings

### 2026-07-17: markdown mode hard-wraps paragraphs; the real unit boundary is the blank line

The clean-HTML fixture rendered to 130 non-empty lines in markdown mode versus 68 in plain mode, because a single newline is a soft line break inside a markdown paragraph, not a unit boundary. A list block is a single blank-delimited block whose items are separated by single newlines, so the splitter must break it into per-item units rather than merging them into a run-on. Emphasis boundaries drop their surrounding space in 16 cases on this fixture (`**Deep research sessions**where`): markdown-it-py alone does not restore it, so the renderer must add a boundary space at emphasis/text adjacencies. The real article contained no fenced code blocks and no blockquotes, confirming the fixture-coverage risk the synthetic snippet was pre-registered against.

### 2026-07-17: trafilatura emits CommonMark-invalid run-in bold that leaks literal `**`

A closing `**` preceded by punctuation and followed by a letter (`**Issue and PR triage/review.**Agents`) fails CommonMark's flanking rule, so markdown-it leaves the markers as literal text. Fixed with a belt-and-suspenders residual pass: after the structural strip, any leftover emphasis marker is turned into a space, which also splits the word the fused markers had run together. Word-boundary restoration for validly-parsed emphasis must be close-side only: restoring it at the open edge too would over-split intra-word emphasis (`super**b**` → "super b").

### 2026-07-17: the synthetic snippet caught a bug the real article could never have surfaced

The real article has no blockquotes; the synthetic snippet exposed that soft-wrap-joining `> ` lines leaks a mid-text `>` into spoken. Fixed by keeping a blockquote block raw so markdown-it parses the quote structurally. This is exactly the refutation work the snippet was built to do.

### 2026-07-17: a code block stays atomic; the right spoken form for it is still unsettled

The synthetic fenced block stays one unit; its spoken form is a `"Code sample."` placeholder: reading code aloud is noise, and the *right* spoken form (a summary, read literally, something else) is left as an open follow-up rather than decided here.

### 2026-07-17: the raw-vs-clean A/B confirms the strip is load-bearing

Synthesizing raw markdown syntax versus the cleaned spoken form and listening to both: raw markdown audibly vocalizes the markdown syntax. This positively confirms the strip is necessary, not incidental: disproof condition 4 would have fired without it.

### 2026-07-17: round-trip on the real fixture: 55 aligned units, 0 dropped, timing exact

55 units, contiguous windows, last `end` == duration (846.23 s ≈ 14 min); zero residual markdown syntax across all 55 spoken units; the user confirmed the cleaned audio reads as natural prose with no vocalized syntax.

### 2026-07-17: production's title/nav cleanup silently stops working under markdown

Replaying production's `_clean_paragraphs` cleanup against the markdown display units showed it drops zero units: its exact-match tests do not see past a leading `#`/`##` markdown prefix. A markdown-aware variant that strips the leading marker before comparing drops the intended units correctly. This is a graduation requirement, not a research finding: the cleanup logic must normalize a leading marker before matching.

## Conclusion

**Cleared.** All five task criteria met and none of the five disproof conditions fired: 55 aligned units with zero residual markdown syntax, timing monotonic and contiguous with last `end` == duration, and user-confirmed clean, natural audio. The mechanism needed no TTS contract change: the service was already index-keyed, and that sameness still holds only by construction rather than by an executing assertion; see [[test-tts-contract-unchanged-by-markdown]]. The real risks were not the HTML→markdown boundary (trafilatura emits coherent markdown) but **segmentation** (the blank-line unit boundary, list-item and blockquote handling) and **the spoken strip** (CommonMark-invalid run-in bold, close-side-only word-boundary restoration), both tractable.

The "reads as natural prose" half of criterion 4 stays exactly what it was here: a human judgment, not a machine-checkable one. See [[decide-audible-markdown-syntax-criterion]] for what to do with that permanently.

**Scope.** Self-use, nagara only, one clean-HTML article end-to-end plus a synthetic snippet for the constructs it lacked. End-to-end proven (audio + timing): inline emphasis, links, headings, lists. Strip-level only, no audio/timing round-trip: blockquote, code, table, and tables additionally need `include_tables=True`, an extraction-side toggle not exercised here. Not evidence of generalization across article types or formatting density, of demand, or of the player UX. Content-cleanup faithfulness (beyond edge cruft) was deliberately out of scope.

---

Related: [[lab/README|the lab]] · [[markdown-formatted-paragraphs]] · [[article-extraction]] · [[read-along-timing]] · [[item-contract]] · [[decide-audible-markdown-syntax-criterion]] · [[test-tts-contract-unchanged-by-markdown]]
