---
title: "Queue"
summary: "Every item is private to the key that created it; a voice is chosen per item or at random from a curated pool, and a status a user can see maps directly onto generating, ready, or failed."
created: "2026-07-29"
---

# Queue

## 🔭 Overview

What a user has, once they have enqueued anything: a private list of items, each an article on its way to becoming listenable audio or already there.

## 🔒 Private by default, single-user for now

An item belongs to whoever's key created it: nobody else can read, poll, or play it (see [authentication](../technical-design/authentication.md)). Today that means exactly one user per deployment: there is no sign-up, no multi-tenancy, and one API key acts as the whole identity. That posture is deliberate for the single-user phase; see [what-nagara-is](what-nagara-is.md) for the build order that opens it up once the open question of whether anyone besides the owner wants this has an audience to build for.

## 🗣️ Voices

Every item carries a voice: named explicitly at creation, or, if omitted, chosen at random from a curated pool of known-good Kokoro voices and then fixed on the item, so a re-poll never changes which voice an item's audio uses. Any voice is explicitly requestable; the random pool is a curated subset.

> [!NOTE] Why the random pool excludes low-grade voices
> An item with no voice named should always sound good, so the pool holds only the voices judged usable. A caller who wants one of the others names it.

## 🟢 States

An item is `generating`, `ready`, or `failed`: the same three states [item-lifecycle](../technical-design/item-lifecycle.md) tracks internally, shown as-is with no separate user-facing vocabulary. A `ready` item has playable audio and a read-along transcript; a `failed` item carries a human-readable reason, whether that is an unreachable URL, an unsupported file type, or a crash partway through.

## 🚫 What the queue is not

Not a general reading list manager, not a bookmarking tool, not a way to upload your own files (see [what-nagara-is](what-nagara-is.md)'s out-of-scope list): only public article URLs, turned into audio.

## ⏩ What is not built yet

- **A visible list of items** with status and a link to each player.
- **Quota as a hard block**, a `GET /items` list endpoint, and API-key create/revoke.
- **A settings surface** for the default voice and key management.

---

Related: [what-nagara-is](what-nagara-is.md) · [authentication](../technical-design/authentication.md) · [item-lifecycle](../technical-design/item-lifecycle.md) · [item-contract](../technical-design/item-contract.md) · [listening-experience](listening-experience.md)
