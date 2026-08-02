---
title: "Audio read-later queue"
tags:
  - quest
summary: "Hand a public article URL to a private service and get back listenable read-along audio, without managing the generation: the backend spine every other slice consumes."
status: solved
kind: build
adventure:
blocked_by: []
priority: 1-now
created: "2026-07-17"
---

# Audio read-later queue

## What

Hand a public article URL to a private service and get back listenable read-along audio, without managing the generation. It has to work for an agent client pushing from a reading list, which means one credential per call and no retry bookkeeping. Constraints settled elsewhere: items are private by definition; a paragraph boundary is the product's responsibility because it drives the highlight.

## Answer

**Promoted: the backend spine.** Built in place at `api/` + `tts/`, hardened during the experiment itself: pydantic-settings, `models`/`service`/`schemas`/`endpoints` packages, `APIKeyHeader` auth on every route, 72 tests. Where it lives: [[item-lifecycle]], [[article-extraction]], [[read-along-timing]], [[tts-service]], [[item-contract]], [[authentication]], [[persistence-and-storage]].

De-risked by [[player-ready-item]], which cleared every unknown it carried:

- URL→paragraph extraction is trustworthy enough to drive a highlight: **yes**, with a plain HTTP fetch (trafilatura handled all four HTML fixtures, including a JS-rendered Substack that server-renders), so the HTML↔headless boundary sits further out than assumed.
- Async-and-poll avoids retry/backoff bookkeeping on an agent client, and a poll tells a running job from a dead one: **yes**. `spawn` plus a non-blocking result read: a timeout is a running job, a re-raised remote exception is a crash with its error.
- The item shape carries everything a read-along player reads: **yes**, per-paragraph `{start, end, text}` plus `duration` and an audio link, scored against a pre-registered checklist with no missing field.
- The async layer needs no broker and no worker process at this scale: **correct**. The compute platform's own invocation primitives are sufficient.

What was knowingly accepted, not cleared: prose-boilerplate paragraphs (footer donations, sponsor asides) arrive as full sentences and are not stripped (see [[prose-boilerplate-stripping]]); single-user, no quota, no key management (see [[queue|the queue]]'s "what is not built yet").

> [!note] The last unknown was accepted, not cleared
> Promoting over an open unknown is normally what a decision refuses to do lightly. This one was accepted knowingly: it is a residual risk on a decision already built, not a blocker to it, and the only thing that could still change is how much cruft survives.

How far the evidence reaches: one session, five real articles from one person's reading list, one machine: not evidence of demand, of generalization beyond these site types, or of multi-user behaviour. [[validate-demand]] is the standing question this leaves open.

---

Related: [[quest-log/README|the quest log]] · [[player-ready-item]] · [[item-lifecycle]] · [[article-extraction]] · [[read-along-timing]] · [[item-contract]] · [[authentication]] · [[validate-demand]]
