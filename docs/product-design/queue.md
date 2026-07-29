---
title: "Queue"
tags:
  - product-design
summary: "Every item is private to the key that created it; a voice is chosen per item or at random from a curated pool, and a status a user can see maps directly onto generating, ready, or failed."
---

# Queue

What a user has, once they have enqueued anything: a private list of items, each an article on its way to becoming listenable audio or already there.

## Private by default, single-user for now

An item belongs to whoever's key created it: nobody else can read, poll, or play it (see [[authentication]]). Today that means exactly one user per deployment: there is no sign-up, no multi-tenancy, and one API key acts as the whole identity. That posture is deliberate for the dogfood phase, not a limitation nobody noticed; see [[what-nagara-is]] for the build order that replaces it once [[validate-demand]] has an audience to build for.

## Voices

Every item carries a voice: named explicitly at creation, or, if omitted, chosen at random from a curated pool of known-good Kokoro voices and then fixed on the item, so a re-poll never changes which voice an item's audio uses. Low-grade voices are deliberately excluded from the random pool so an un-voiced item always sounds good; any voice remains explicitly requestable regardless.

## The statuses a user sees

An item is `generating`, `ready`, or `failed`: the same three states [[item-lifecycle]] tracks internally, shown as-is with no separate user-facing vocabulary. A `ready` item has playable audio and a read-along transcript; a `failed` item carries a human-readable reason, whether that is an unreachable URL, an unsupported file type, or a crash partway through.

## What the queue is not

Not a general reading list manager, not a bookmarking tool, not a way to upload your own files (see [[what-nagara-is]]'s out-of-scope list): only public article URLs, turned into audio.

## What is not built yet

- **A visible list of items with status and a link to each player**: see [[article-list]].
- **Quota as a hard block**, a `GET /items` list endpoint, and API-key create/revoke: see [[api-hardening]].
- **A settings surface** for the default voice and key management: see [[settings]].

---

Related: [[what-nagara-is]] · [[authentication]] · [[item-lifecycle]] · [[item-contract]] · [[listening-experience]] · [[pricing-model]]
