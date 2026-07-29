---
title: "Audio read-later queue"
tags:
  - idea
summary: "Hand a public article URL to a private service and get back listenable read-along audio, without managing the generation: the backend spine every other slice consumes."
status: promoted
priority: next
impact: high
size: large
experiments:
  - "[[player-ready-item]]"
---

# Audio read-later queue

## Objective

Hand a public article URL to a private service and get back listenable read-along audio, without managing the generation. It has to work for an agent client pushing from a reading list, which means one credential per call and no retry bookkeeping. Constraints settled elsewhere: items are private by definition; a paragraph boundary is the product's responsibility because it drives the highlight.

## Unknowns

- ~~Can URL→paragraph extraction be made trustworthy enough that its boundaries can drive a highlight?~~ → **Yes, with a plain HTTP fetch.** trafilatura handled all four HTML fixtures including a JS-rendered Substack post (it server-renders its content), so the HTML↔headless boundary sits considerably further out than assumed. [[player-ready-item]]
- ~~Does an async-and-poll shape avoid pushing retry/backoff bookkeeping onto an agent client, and can a poll tell a running job from a dead one?~~ → **Yes.** `spawn` plus a non-blocking result read: a timeout is a running job, a re-raised remote exception is a crash with its error. [[player-ready-item]]
- ~~Does the item shape carry everything a read-along player reads?~~ → **Yes**: per-paragraph `{start, end, text}` plus `duration` and an audio link, scored against a pre-registered checklist with no missing field. [[player-ready-item]]
- ~~Does the async layer need a broker and a worker process at this scale?~~ → **No.** The compute platform's own invocation primitives are sufficient. [[player-ready-item]]
- Prose-boilerplate paragraphs (footer donations, sponsor asides) arrive as full sentences and are not stripped. Carried knowingly; see [[prose-boilerplate-stripping]].

> [!note] The last unknown was accepted, not cleared
> Promoting over an open unknown is normally what a decision refuses to do lightly. This one was accepted knowingly: it is a residual risk on a decision already built, not a blocker to it, and the only thing that could still change is how much cruft survives.

## Conclusion

**Promoted: the backend spine.** Built in place at `api/` + `tts/`, hardened during the experiment itself: pydantic-settings, `models`/`service`/`schemas`/`endpoints` packages, `APIKeyHeader` auth on every route, 72 tests. Where it lives: [[item-lifecycle]], [[article-extraction]], [[read-along-timing]], [[tts-service]], [[item-contract]], [[authentication]], [[persistence-and-storage]].

What was knowingly accepted: crude prose-boilerplate stripping (see [[prose-boilerplate-stripping]]); single-user, no quota, no key management (see [[queue|the queue]]'s "what is not built yet").

How far the evidence reaches: one session, five real articles from one person's reading list, one machine: not evidence of demand, of generalization beyond these site types, or of multi-user behaviour. [[validate-demand]] is the standing question this leaves open.

---

Related: [[lab/README|the lab]] · [[player-ready-item]] · [[item-lifecycle]] · [[article-extraction]] · [[read-along-timing]] · [[item-contract]] · [[authentication]] · [[validate-demand]]
