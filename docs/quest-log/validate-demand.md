---
title: "Validate demand"
tags:
  - adventure
summary: "Find out whether anyone besides the owner wants a private audio read-later queue."
status: open
kind: raid
priority: 1-now
created: "2026-07-17"
---

# Validate demand

## Destination

Find out whether anyone besides the owner wants a private audio read-later queue. Everything else in this repository exists to make that answerable: the TTS pipeline is de-risked ([[audio-read-later-queue]], [[markdown-formatted-paragraphs]]), the compute cost is settled at roughly $0.008 per article ([[tts-service]]), and what is unproven is the product shape and whether there is an audience. Reaching the end means a stranger has come to nagara, queued a real item, and come back.

## Bearings

**The ground.** The product surface a stranger meets: the funnel (landing, auth, article creation), the queue, and the player. Not the extraction pipeline internals or the TTS cost, which are settled.

**Read first.** [[what-nagara-is]] for what is deliberately out of MVP scope; [[queue]]'s "what is not built yet" for the agreed build order; the solved spine ([[audio-read-later-queue]], [[markdown-formatted-paragraphs]]) for what is already proven; [[tts-service]] for the per-article cost.

**Standing preferences.** The public-funnel cluster (real auth, onboarding, a landing page) exists in service of this question and nothing else, in the build order agreed 2026-07-17. Pricing waits for an audience to price for ([[pricing-model]] is a loose quest that depends on this). And the confound learned in [[read-along-player-shape]]: a builder-driven loop validates shape, never demand, and must not masquerade as validated demand.

> [!info] A private sibling vault names the wider product idea this MVP validates
> A sibling repository outside this one (`shin-sekai`, an unversioned personal notes vault) holds the original idea write-up and its MVP scope decision. It is not linked here because it is unreachable from this repository and would be a dead reference to anyone else; the parts of it that matter to building nagara (what is deliberately out of MVP scope) are inlined in [[what-nagara-is]] instead.

## Trials

Candidate experiments a future session could clear, not yet phrased as single quests:

- Whether a paste-a-URL public hook converts a stranger into a first queued item.
- Whether a bundle-of-items or a metered-audio-minutes framing reads better.
- What a stranger does on their second visit.
- Whether an acquisition surface like [[save-to-nagara-bookmarklet]] changes any of that.

Each graduates into a quest the moment it can be stated as one session's worth of work.

## Solved

Nothing yet. The public-funnel build quests ([[auth]], [[landing]], [[article-creation]]) are what make the question answerable; the trials above are what get answered once strangers can reach nagara.

## Out of scope

- **Multi-user scaling before validation.** Quota, key management, and multi-user behaviour are not this adventure's question; they are worth building only if the answer is yes.
- **Pricing before an audience.** [[pricing-model]] waits on this adventure reaching an audience to price for.

---

Related: [[quest-log/README|the quest log]] · [[audio-read-later-queue]] · [[markdown-formatted-paragraphs]] · [[what-nagara-is]] · [[queue]] · [[pricing-model]] · [[save-to-nagara-bookmarklet]] · [[auth]] · [[landing]] · [[article-creation]]
