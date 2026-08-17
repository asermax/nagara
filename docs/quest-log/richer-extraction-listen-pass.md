---
title: "Richer extraction listen pass"
tags:
  - quest
summary: "Play every changed spoken form through the real Modal path and hear it, paying the debt four design quests each left open."
status: solved
kind: build
adventure: richer-extraction
blocked_by: []
priority: 3-later
created: "2026-08-02"
---

# Richer extraction listen pass

## What

Generate audio for every spoken form [[richer-extraction]] changed, play it, and judge it by ear.

This is not a test and it cannot be one. The project's standing rule is that a strip regression is invisible in a diff, inaudible in a test summary, and unmistakable in one second of audio. Four design quests decided what a listener hears **by reading alone** and each flagged the debt as owed.

One quest paid part of it. The describer-prompt work put 16 candidate clips through the production Modal `Kokoro` path and heard them, which is how the `Code: This example demonstrates…` stutter, the fluent-but-wrong invention, and an unsanitized backtick became audible rather than theoretical. That discharged the debt **for the describer-prompt layer only**.

Everything else is unpaid.

## Design

### Partly paid already, for wave 1

**Heard and passed 2026-08-02**, before this quest was takeable: the fence recovery and the boundary repair, on `realpython.com/python-first-steps/` through the production Modal path (item `itm_eac284d7`, 71.3 minutes, 416 units).

That article is the one the fence bug was measured on, and it is the strongest case in the corpus: unit 358 alone is nine minutes of prose that used to be the two-word string `"Code sample."`. Spoken words went from 6,543 to 10,086.

So two rows of the table below are already struck. What remains is everything the describer touches, which is what this quest was written for.

### What has to be heard

| Change | The judgement only a listener can make |
|---|---|
| `Code: ` prefix on a real article | whether it lands as a clean cue or a stutter, seventy times in one tutorial |
| one sentence over a 21-line code window | whether it feels rushed or right |
| `Code with no description.` | honest, or flat |
| `Image: ` prefix | whether the announcement reads naturally against the prose around it |
| a caption spoken verbatim | whether an author's caption reads as part of the article or as an interruption |
| `Image with no description.` | honest, or flat |
| the fenced-prose re-classification | that the recovered ~3,687 words actually read as prose, not as mangled code |
| the boundary repair | that `realpart` and `AGENTS.md(or` are gone, and nothing new fused |
| a full code-heavy article end to end | the cumulative effect: does 25 descriptions plus floors past the cap sound coherent, or does it turn into a list |

### The method

Synthesize through the same Modal `Kokoro` the API calls, not a local approximation. That is what made the earlier pass trustworthy: it exercised the production path rather than something that resembled it.

Enqueue real corpus articles rather than synthetic snippets. The failures worth catching are cumulative and contextual, and a snippet cannot produce them. The code-heavy tutorial and the New Yorker photo essay are the two that stress the most decisions at once.

`prototype_listen.py` on `idea/describer-prompt-design` is the harness that already did this once, with its 16 clips and manifest in `prototype_cache/listen/`. Reuse it rather than rebuilding.

> [!warning] Generated audio never enters the repository
> `.gitignore` refuses `*.ogg`, `*.wav`, `*.mp3` and the rest, deliberately: every audio file is regenerable for fractions of a cent and one accidental commit is worth more than the rest of the history. Keep the clips outside the tree, and record the judgement in this quest's answer instead.

### What a finding here means

A defect found by ear is a defect in the quest that introduced it, not in this one. This quest's output is the judgement and the list; the fix goes back to the slice that owns it.

The one thing that would make this quest fail rather than report is a marker reaching narration, because the whole two-guard design of structured output plus sanitize exists to make that impossible and the leak that motivated it was **stochastic**. Hearing one means a guard is wrong rather than unlucky.

### What it does not cover

Whether the item is the right article. A 200-status error page synthesizes fluently and sounds fine, so listening cannot catch it. That is [[trustworthy-extraction]]'s, and [[plain-fetch-hardening]] closed only the 403 case.

## Answer

**Passed by ear.** Both corpus articles were generated through the real Modal `Kokoro` path and heard: the code-heavy Real Python tutorial (70.7 min, 419 units, 64 code, 3 image) and the New Yorker photo essay (20.7 min, 26 units, 5 image). They sound fine. No hard-fail: no markdown marker is audible in any describer output.

**The describer layer is clean.** Across roughly 25 real describes over the two articles, zero `Code:`/`Image:` unit leaked a marker, so the structured-output-plus-sanitize design held on real data. The `Code: ` prefix reads as a clean cue rather than a stutter, a caption reads as the author's own voice (case 1), a generated image sentence respects the invention guard (it read the written word "VOGUE" rather than naming the sitter), and the cap floors (40 `describe cap reached` on Real Python, the combined budget working) sound coherent rather than abrupt. Timing aligned on both (419/419, 26/26).

**Two text-level findings from the manifest marker scan**, neither audible as a defect:

- A **table cell** read its inline-code backtick, because the table path was the one spoken derivation that never ran through `sanitize_spoken`. Fixed at the table path (`fix(api): sanitize a linearized table's spoken form`).
- **REPL and code flattened into prose** on the Real Python tutorial: trafilatura rendered multi-statement code as inline-code spans inside prose paragraphs, so code is spoken as prose. Not a marker leak and not a sanitize gap; split out into its own quest, [[code-spoken-as-prose]].

**Method.** A throwaway harness ran the real pipeline (fetch, image acquisition, Gemini describer) and the same `spawn_synthesis` Modal path the API calls, wrote the audio outside the repo, and emitted a manifest of every spoken form plus a marker scan. Audio never enters the tree, per the rule; the verdict lives here.

**What it does not cover.** Whether an item is the right article, which is [[trustworthy-extraction]]'s.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[describe-code-blocks]] · [[describe-article-images]] · [[article-figure-captions]] · [[code-spoken-as-prose]] · [[trustworthy-extraction]]
