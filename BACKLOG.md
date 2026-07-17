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

- **API hardening** — furniture deferred out of the
  [001](experiments/001-player-ready-item/README.md) spike, not yet built (the spine itself is in place,
  see `PRODUCT.md` M1): **quota enforcement** (per-user item-count tiers), a **`GET /items` list
  endpoint**, and **API-key create/revoke** (also surfaces in Settings).
- **Article UI (read-along player)** — audio + paragraph highlighting synced to `currentTime` +
  click-to-seek. The wow moment and the highest UX uncertainty of the visual pieces.
- **Article list (queue)** — items with status (`queued → generating → ready`) + a link to each player.
- **Settings** — default voice (all Kokoro voices + Random) + API key create/revoke.

*Public-funnel cluster — turns it into something strangers can try (serves the demand question):*

- **Auth** — Google OAuth login + the pasted-URL-survives-redirect stash/replay. Replaces the
  single-user shim from the dogfood cluster.
- **Article creation** — the authenticated web enqueue flow (paste URL in-app → item). *May merge
  with Landing.*
- **Landing** — public demo hook: paste a URL → stash → login → replay as your first queued item.

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
- **Unify web + API under one domain.** Serve the web frontend and the API from a single origin (e.g.
  `nagara.asermax.com`) instead of separate hosts. Railway maps a domain to one service, so one surface
  must own the domain and route to the other over private networking. Preferred shape: the TanStack
  Start server owns the domain and proxies `/api/*` to the api service (`nagara-api.railway.internal:8080`);
  alternatives are a dedicated reverse-proxy service or a Cloudflare Worker doing path routing. Payoff:
  same-origin — no CORS, simpler cookie/session auth for the future player, clean presigned-audio flow.
  Do when the web frontend lands.
- **Markdown extraction: faithfulness + is-it-worth-it.** Parked from
  [experiment 002](experiments/002-markdown-paragraphs/README.md), which narrowed to pipeline
  *integrity* (does markdown break TTS/timing) and treated these two as givens. Faithfulness: does
  trafilatura's markdown output preserve *real* inline/block formatting cleanly (the inline analogue of
  001's split-quality check)? Worth-it: once a read-along player exists, does displayed formatting
  meaningfully improve the read/listen experience enough to justify the added contract + render
  complexity? The worth-it lens is best judged with a player in hand.
- **Markdown pipeline: end-to-end validation on a formatting-heavy fixture.** Experiment 002 proved the
  markdown feature (all six construct classes) but judged only a clean-HTML article (Mitchell Hashimoto)
  **end-to-end**; blockquote/code/table are **strip-level only**, and tables need `include_tables=True`
  (untested extraction toggle). Re-run the integrity check end-to-end (extraction → strip → TTS → audio +
  timing) against a deliberately formatting-heavy article (code, nested lists, blockquotes, a real
  table), and confirm `include_tables=True` doesn't degrade extraction precision elsewhere.
- **Right spoken form for code blocks.** Experiment 002 keeps a fenced code block as one atomic unit and
  speaks a `"Code sample."` placeholder (accepted interim default). Explore the right read-along
  treatment — placeholder vs skip-with-highlight vs a short description vs reading it literally — as its
  own small experiment when the player exists to judge the UX.

## Later / deferred

*Deliberately out of the MVP (see `../../shin-sekai/02_Areas/Ideas/audio-article-product/mvp.md`):*

- **File uploads** (PDFs / docs) — a whole content-ingestion surface of its own.
- **Paywalled content** — technical *and* legal/ethical; sidestepped by the public-articles-only posture.
- **Audio caching by `(url, voice)`** — nice optimization, skipped for now.
- **Payment / upgrade flow + paid tier** — quota just hard-blocks for the MVP; monetize after demand is proven.
- **Multiple API keys per user** — one key per user is enough for now.
- **"Save to Nagara" bookmarklet / browser extension** — good acquisition + capture surface, deferred.
- **Decay-based queue cleanup** — automatic pruning of old items.
- **AAC 48k audio fallback** — only if older-Safari (< 17) support turns out to matter; Opus ships first.
