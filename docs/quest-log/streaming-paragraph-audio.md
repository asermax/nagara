---
title: "Streaming paragraph audio"
tags:
  - adventure
summary: "Stream paragraphs sequentially from one warm container instead of waiting for the whole article, for a fast first-audio and to avoid generating an article a listener never finishes."
status: open
kind: journey
priority: 2-soon
created: "2026-07-17"
---

# Streaming paragraph audio

## Destination

Paragraphs stream sequentially from one warm container instead of the whole article rendering before anything is playable. Two payoffs, and both have to land: a time-to-first-audio of roughly one to two seconds rather than the current whole-article wait, for a better perceived start; and lazy generation, synthesizing paragraphs only as the listener reaches them, so an article nobody finishes is not paid for in full.

## Bearings

**The ground.** The TTS service and the item lifecycle: how audio is generated, when an item becomes `ready`, and what a client is promised at that point. Not extraction, and not the player's visual behaviour beyond the timing contract it depends on.

**Read first.** [[tts-service]] for how generation runs today and what a warm container costs; [[item-lifecycle]] for what `ready` currently guarantees; [[read-along-timing]] for the contract lazy generation would have to keep.

**Standing preferences.** The second payoff is the one that constrains the design: a fast first-audio is achievable by prefetching, and that would still generate the whole article. Any shape that only buys perceived speed has answered half the question.

## Trials

- Whether one warm Modal container can serve paragraphs sequentially at that latency.
- Whether lazy per-paragraph generation is achievable without breaking the read-along contract's assumption that a `ready` item's full timeline already exists.

## Solved

Nothing yet.

## Out of scope

- **Changing the TTS provider.** This adventure is about how generation is scheduled and delivered, not about who does it.

---

Related: [[quest-log/README|the quest log]] · [[tts-service]] · [[item-lifecycle]] · [[read-along-timing]]
