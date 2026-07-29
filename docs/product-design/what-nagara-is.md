---
title: "What nagara is"
tags:
  - product-design
summary: "A private, API-first audio read-later queue (hand it a URL, get back listenable read-along audio) built to answer one open question: does anyone besides the owner want this?"
---

# What nagara is

**Nagara (ながら)**: from *ながら聞き*, consuming content *while doing something else*. A private, API-first **audio read-later queue**: "Pocket or Instapaper, but for audio."

## What one enqueue call does

`enqueue(url, voice?) → generate eagerly → a private item in your queue with a listen link.` Nothing about this primitive requires a person at a keyboard: an agent client can push a URL from a reading list with one credential and no interactive step, which is why it is the API that is the real product and the paste-and-listen web page is only the front door onto the same call. See [[queue|the queue]] for what a person sees once an item exists, and [[item-contract]] for the exact shape the call returns.

## What is already settled

The TTS pipeline is proven, not a risk this product still carries: Kokoro-82M on Modal L4 renders an article for roughly **$0.008**, and paragraph-level read-along timing is solved (see [[tts-service]], [[read-along-timing]]). What remains genuinely open is **demand**: whether anyone besides the owner wants a private audio read-later queue at all. See [[validate-demand]] for that standing question and what would answer it.

> [!note] Why the MVP exists to answer a demand question rather than to ship a finished product
> Building further product surface before knowing whether anyone wants the thing would be speculative work against an unanswered question. The public-funnel slices ([[auth]], [[article-creation]], [[landing]]) exist specifically to make that question answerable, not because the dogfood cluster needs them.

## What is not built yet, in order

Agreed with the user on 2026-07-17, in two clusters. The **dogfood cluster** hardens the single-user pipeline that already works: [[api-hardening]] (quota, a list endpoint, key CRUD), then [[article-list]] (the queue view), then [[settings]] (voice default, key management). The **public-funnel cluster** turns the product into something a stranger can try, each slice built in service of [[validate-demand]]: [[auth]] (Google OAuth plus a paste-then-login replay), then [[article-creation]], then [[landing]].

## What is deliberately out of scope

- **File uploads** (PDFs, documents): a whole content-ingestion surface of its own, not this product's.
- **Paywalled content**: sidestepped by a public-articles-only posture, both a technical and a legal/ethical boundary.
- **Payment and a paid tier**: quota just hard-blocks for now (see [[queue|the queue]]); monetization waits until demand is proven.
- **Multiple API keys per user**: one key per user is enough at this stage.
- **Decay-based queue cleanup**: no automatic pruning of old items.
- **AAC 48k audio fallback**: Opus ships first; this is reached for only if pre-17 Safari support turns out to matter.

> [!info] A private sibling vault named the wider product idea this MVP validates
> See [[validate-demand]]'s callout: the original idea write-up lives outside this repository and is not linked here for that reason.

---

Related: [[queue]] · [[listening-experience]] · [[what-gets-read-aloud]] · [[validate-demand]] · [[audio-read-later-queue]] · [[tts-service]]
