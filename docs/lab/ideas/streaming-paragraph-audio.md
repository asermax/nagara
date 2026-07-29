---
title: "Streaming paragraph audio"
tags:
  - idea
summary: "Stream paragraphs sequentially from one warm container instead of waiting for the whole article, for a fast first-audio and to avoid generating an article a listener never finishes."
status: framed
priority: soon
impact: high
size: large
experiments:
---

# Streaming paragraph audio

## Objective

Stream paragraphs sequentially from one warm container instead of waiting for the whole article to render before anything is playable. Two payoffs: a time-to-first-audio of roughly one to two seconds instead of the current whole-article wait, better perceived start; and generating lazily: only synthesizing paragraphs as the listener actually reaches them, avoiding preemptive whole-article generation and its compute cost when a listener bails early.

## Unknowns

Not yet enumerated as something a single experiment could clear. Candidates already named: whether one warm Modal container can serve paragraphs sequentially at that latency; whether lazy per-paragraph generation is achievable without breaking the read-along contract's assumption that a `ready` item's full timeline already exists.

---

Related: [[lab/README|the lab]] · [[tts-service]] · [[item-lifecycle]] · [[read-along-timing]]
