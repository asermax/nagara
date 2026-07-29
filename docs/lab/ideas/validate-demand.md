---
title: "Validate demand"
tags:
  - idea
summary: "Find out whether anyone besides the owner wants a private audio read-later queue."
status: framed
priority: next
impact: high
size: large
experiments:
---

# Validate demand

## Objective

Find out whether anyone besides the owner wants a private audio read-later queue. Everything else in this repository exists to make that answerable: the TTS pipeline is de-risked ([[audio-read-later-queue]], [[markdown-formatted-paragraphs]]), the compute cost is settled at roughly $0.008 per article ([[tts-service]]), and what is unproven is the product shape and whether there is an audience.

Already settled: the public-funnel work (real auth, onboarding, a landing page) exists in service of this question and nothing else; see [[queue|the queue]]'s "what is not built yet" for the agreed build order it sits in.

Candidates a future experiment could clear, not yet enumerated as unknowns: whether a paste-a-URL public hook converts a stranger into a first queued item; whether a bundle-of-items or a metered-audio-minutes framing reads better (see [[pricing-model]]); what a stranger does on their second visit; whether an acquisition surface like [[save-to-nagara-bookmarklet]] changes any of that.

> [!info] A private sibling vault names the wider product idea this MVP validates
> A sibling repository outside this one (`shin-sekai`, an unversioned personal notes vault) holds the original idea write-up and its MVP scope decision. It is not linked here because it is unreachable from this repository and would be a dead reference to anyone else; the parts of it that matter to building nagara (what is deliberately out of MVP scope) are inlined in [[what-nagara-is]] instead.

---

Related: [[lab/README|the lab]] · [[audio-read-later-queue]] · [[markdown-formatted-paragraphs]] · [[what-nagara-is]] · [[queue]] · [[pricing-model]] · [[save-to-nagara-bookmarklet]]
