# Backlog

Immature ideas live here until they become pre-registered experiments. **Capturing is free** —
drop anything in with `/capture`; ordering and pruning happen later.

- `## Next up` — the ordered priority queue (top = run first), curated by `/prioritize`.
- `## Ideas` — the default landing spot for a fresh capture.
- `## Later / deferred` — things consciously parked (out of MVP scope, blocked, or waiting on a signal).

## Next up

The MVP, decomposed into buildable slices (spike-at-root). Order agreed with the user 2026-07-17.
Two clusters: a **dogfood** path (user zero via Tachikoma, **single-user, no login** for now) and a
**public-funnel** path (real auth + onboarding, built in service of the *demand* question). The
spine is the API; everything else consumes it.

*Dogfood cluster — single-user, no login yet:*

1. ~~**API**~~ → promoted to **[experiment 001](experiments/001-player-ready-item/README.md)** (in
   progress): does a real push yield a player-ready item. Deferred out of the 001 spike as furniture
   for a later **API-hardening** pass — not needed to answer 001's question: **quota enforcement**
   (per-user item-count tiers), a **`GET /items` list endpoint**, and **API-key create/revoke** (also
   surfaces in Settings #4).
2. **Article UI (read-along player)** — audio + paragraph highlighting synced to `currentTime` +
   click-to-seek. The wow moment and the highest UX uncertainty of the visual pieces.
3. **Article list (queue)** — items with status (`queued → generating → ready`) + a link to each player.
4. **Settings** — default voice (all Kokoro voices + Random) + API key create/revoke.

*Public-funnel cluster — turns it into something strangers can try (serves the demand question):*

5. **Auth** — Google OAuth login + the pasted-URL-survives-redirect stash/replay. Replaces the
   single-user shim from the dogfood cluster.
6. **Article creation** — the authenticated web enqueue flow (paste URL in-app → item). *May merge
   with Landing.*
7. **Landing** — public demo hook: paste a URL → stash → login → replay as your first queued item.

## Ideas

- **Pricing UX: bundling vs. metering.** Compute cost is settled (~$0.008/article); the open
  question is how to package it for users — a flat bundle of items vs. metered audio-minutes.
- **Streaming paragraph audio.** Stream paragraphs sequentially from one warm container for
  ~1–2 s time-to-first-audio instead of waiting for the whole article. Better perceived start.
- **Prose-boilerplate stripping in extraction.** Footer/donation/sponsor-aside paragraphs that
  trafilatura leaves as full sentences (seen on the magazine + newsletter fixtures). The 001 spike
  strips only safe edge cruft (title echo, nav labels, footnote glyphs, punctuation-only); removing
  prose boilerplate needs a smarter per-site or heuristic pass without over-trimming real content.
- **Caption export (.vtt / .srt).** Generate caption files from Kokoro's word timestamps.
- **Random voice resolution.** Per-user default + a "Random" option that resolves to a concrete voice
  at generation time and is stored on the item (so re-listens stay stable). Hardcoded to one voice in
  the 001 spike; nothing there tests it.
- **Non-English read-along depth.** Paragraph highlighting already works in any language; word-level
  highlighting is English-only (espeak languages return no word timestamps). Explore alternatives.

## Later / deferred

*Deliberately out of the MVP (see `../../shin-sekai/02_Areas/Ideas/audio-article-product/mvp.md`):*

- **File uploads** (PDFs / docs) — a whole content-ingestion surface of its own.
- **Paywalled content** — technical *and* legal/ethical; sidestepped by the public-articles-only posture.
- **Audio caching by `(url, voice)`** — nice optimization, skipped for now.
- **Payment / upgrade flow + paid tier** — quota just hard-blocks for the MVP; monetize after demand is proven.
- **Multiple API keys per user** — one key per user is enough for now.
- **"Save to Nagara" bookmarklet / browser extension** — good acquisition + capture surface, deferred.
- **Postgres + Railway production infra** — graduate storage from the spike's SQLite to Postgres and
  deploy on Railway (the intended production target). SQLAlchemy is already in place to ease it.
- **Auth for audio delivery (graduation)** — audio currently requires the `X-API-Key` header, but a
  browser `<audio>` element can't send one; needs signed URLs or session-cookie auth so the future
  player can stream without exposing audio publicly.
- **Decay-based queue cleanup** — automatic pruning of old items.
- **AAC 48k audio fallback** — only if older-Safari (< 17) support turns out to matter; Opus ships first.
