---
title: "What nagara is"
summary: "A private, API-first audio read-later queue (hand it a URL, get back listenable read-along audio) built to answer one open question: does anyone besides the owner want this?"
created: "2026-07-29"
---

# What nagara is

## 🔭 Overview

**Nagara (ながら)**: from *ながら聞き*, consuming content *while doing something else*. A private, API-first **audio read-later queue**: "Pocket or Instapaper, but for audio."

## ➡️ What one enqueue call does

`enqueue(url, voice?) → generate eagerly → a private item in your queue with a listen link.` Nothing about this primitive requires a person at a keyboard: an agent client can push a URL from a reading list with one credential and no interactive step, which is why the API is the real product and the paste-and-listen web page is one client of the same call. See [the queue](queue.md) for what a person sees once an item exists, and [item-contract](../technical-design/item-contract.md) for the exact shape the call returns.

## ✅ What is already settled

The TTS pipeline is proven: Kokoro-82M on Modal L4 renders an article for roughly **$0.008**, and paragraph-level read-along timing is solved (see [tts-service](../technical-design/tts-service.md), [read-along-timing](../technical-design/read-along-timing.md)). What remains open is **demand**: whether anyone besides the owner wants a private audio read-later queue at all.

> [!NOTE] Why the MVP exists to answer a demand question rather than to ship a finished product
> Building further product surface before knowing whether anyone wants the thing would be speculative work against an unanswered question. The public-funnel pieces (a login, article creation by a stranger, a landing page) exist to make that question answerable; the single-user pipeline does not need them.

## ⏩ What is not built yet, in order

Two groups, in order. The **dogfood group** hardens the single-user pipeline that already works: API hardening (quota, a list endpoint, key CRUD), then the queue view listing a user's items, then a settings surface (voice default, key management). The **public-funnel group** turns the product into something a stranger can try, each piece built to answer the demand question: a login (Google OAuth plus a paste-then-login replay), then article creation by a signed-in stranger, then a landing page.

## 🚫 What is deliberately out of scope

- **File uploads** (PDFs, documents): a whole content-ingestion surface of its own, not this product's.
- **Paywalled content**: sidestepped by a public-articles-only posture, both a technical and a legal/ethical boundary.
- **Payment and a paid tier**: quota just hard-blocks for now (see [the queue](queue.md)); monetization waits until demand is proven.
- **Multiple API keys per user**: one key per user is enough at this stage.
- **Decay-based queue cleanup**: no automatic pruning of old items.
- **AAC 48k audio fallback**: Opus ships first; this is reached for only if pre-17 Safari support turns out to matter.

This MVP validates a narrower part of a larger product idea, whose write-up lives in a private vault outside this repository.

---

Related: [queue](queue.md) · [listening-experience](listening-experience.md) · [what-gets-read-aloud](what-gets-read-aloud.md) · [tts-service](../technical-design/tts-service.md)
