# Backlog

Immature ideas live here until they become pre-registered experiments. **Capturing is free** —
drop anything in with `/capture`; ordering and pruning happen later.

- `## Next up` — the ordered priority queue (top = run first), curated by `/prioritize`.
- `## Ideas` — the default landing spot for a fresh capture.
- `## Later / deferred` — things consciously parked (out of MVP scope, blocked, or waiting on a signal).

## Next up

*Dogfood findings — captured 2026-07-20…23 while listening to real articles through Tachikoma. The
first three are defects in the extraction/fetch path (they produce wrong or unusable audio), the rest
are read-along gaps the real listening surfaced:*

- **Extraction: inline formatting joins to the preceding text.** Links and other inline-formatted runs
  lose the space separating them from the text before, e.g. `click here<a href=…>link</a>` instead of
  `click here <a href=…>link</a>`. Corrupts both the spoken audio and the rendered read-along text.
  Adjacent to the markdown-faithfulness question under *Ideas*, but this one is a plain defect.
- **Extraction: reject error pages that return `200`.** A URL serving a GitHub Pages 404 (HTTP `200` +
  an HTML error page) extracts *successfully*, so the pipeline generates audio of the error page being
  read aloud — the worst failure mode, because it looks like a working item. Nothing catches it: the
  status is never `failed`. Fix: validate the extracted paragraphs carry real content (title, length,
  known error-page shapes) before accepting a result.
- **Fetching: pages a plain HTTP request can't reach.** X/Twitter URLs fail extraction outright
  (JS-rendered), and Cloudflare-guarded pages answer `403` with `text/plain`. Proposal: fetch through
  **firecrawl or a similar rendering proxy**, and/or **accept pre-rendered HTML** as an input
  alternative to a URL. Verified out-of-band that a firecrawl-rendered tweet feeds the pipeline fine,
  so the content itself is synthesizable — only the fetch step is missing.
- **Quote voice switching.** Detect quoted passages and switch the Kokoro voice for them, the way
  audiobook narrators differentiate dialogue. Open calls: attribution/nesting detection quality, and
  whether the read-along highlight should signal the switch visually.
- **Image extraction + alt text in the read-along.** Carry article images through extraction and render
  them in the player alongside the text, and **speak their alt text** so listeners aren't silently
  skipping content the reader would see. Overlaps *Focus-mode polish for non-prose constructs* — an
  image is another unit that shouldn't be centre-scaled like prose.
- **Player: link to original + share.** Surface a link to the source article from the player, plus a
  share action that shares the **original URL** (not the player link).

The MVP, decomposed into buildable slices (spike-at-root). Order agreed with the user 2026-07-17.
Two clusters: a **dogfood** path (user zero via Tachikoma, **single-user, no login** for now) and a
**public-funnel** path (real auth + onboarding, built in service of the *demand* question). The
spine is the API; everything else consumes it.

*Dogfood cluster — single-user, no login yet:*

- **API hardening** — furniture deferred out of the
  [001](experiments/001-player-ready-item/README.md) spike, not yet built (the spine itself is in place,
  see `PRODUCT.md` M1): **quota enforcement** (per-user item-count tiers), a **`GET /items` list
  endpoint**, and **API-key create/revoke** (also surfaces in Settings).
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
- **Streaming paragraph audio.** Stream paragraphs sequentially from one warm container instead of
  waiting for the whole article. Two payoffs: (a) ~1–2 s time-to-first-audio, better perceived start;
  (b) generate lazily — only synthesize paragraphs as the listener reaches them, avoiding preemptive
  whole-article generation and its compute cost when a listener bails early.
- **Prose-boilerplate stripping in extraction.** Footer/donation/sponsor-aside paragraphs that
  trafilatura leaves as full sentences (seen on the magazine + newsletter fixtures). The 001 spike
  strips only safe edge cruft (title echo, nav labels, footnote glyphs, punctuation-only); removing
  prose boilerplate needs a smarter per-site or heuristic pass without over-trimming real content.
- **Resume-position backend endpoint.** A real `PATCH`-position endpoint (+ storage) so playback
  position persists server-side and follows the listener across devices. Experiment
  [003](experiments/003-read-along-player/README.md) fakes this with localStorage to judge the resume
  *UX*; the durable cross-device round-trip is graduation furniture, do when the player graduates.
- **Read-along player visual design.** Experiment
  [003](experiments/003-read-along-player/README.md) settled the player's *shape* (layout, UX, the
  E-default + focus-mode structure) with a deliberately-placeholder aesthetic. A separate experiment
  should develop the *proper visual design* — design language, typography, colour, motion, light/dark,
  brand feel — for the player (and by extension the web surface), now that the shape is fixed. Judged on
  aesthetic coherence/quality against real content, with the settled shape as the fixed substrate.
- **Caption export (.vtt / .srt).** Generate caption files from Kokoro's word timestamps.
- **Random voice resolution.** Per-user default + a "Random" option that resolves to a concrete voice
  at generation time and is stored on the item (so re-listens stay stable). Hardcoded to one voice in
  the 001 spike; nothing there tests it.
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
- **Markdown pipeline: blockquote + table validation end-to-end.** Experiment
  [003](experiments/003-read-along-player/README.md) validated headings, nested lists, and code
  **end-to-end** (extraction → strip → TTS → audio + timing → render + highlight) on the Fowler fixture;
  **blockquote and tables remain unverified** (Fowler carried neither, and the pre-registered synthetic
  probe went unbuilt). Re-run the integrity check on an article that has a **real blockquote and a real
  table**, and confirm `include_tables=True` (untested extraction toggle) doesn't degrade extraction
  precision elsewhere.
- **Right spoken form for code blocks.** The pipeline keeps a fenced code block as one atomic unit and
  speaks a `"Code sample."` placeholder (interim default), while the player now renders it with syntax
  highlighting. Explore the right read-along treatment — the promising direction is an **LLM step that
  produces a short spoken explanation of what the code does** (vs. the placeholder / skip-with-highlight /
  reading it literally). Judge the UX with the player in hand.
- **Playback speed control.** Let the listener change playback rate (e.g. 1×/1.25×/1.5×/2×). Straightforward
  on the `<audio>` element; worth an experiment on the control's UX and whether highlight sync holds across
  rates.
- **Focus-mode polish for non-prose constructs.** In the player's focus (teleprompter) mode the active
  unit is centre-aligned + scaled; that reads well for prose but **looks wrong for lists, code, and
  tables** (centring breaks their left-aligned structure). Needs per-construct handling (e.g. keep
  lists/code left-aligned even when the active unit is centred/enlarged).
- **Player real-device mobile check.** The player's mobile breakpoint (ToC hidden, subtler focus zoom,
  smaller control bar) is coded but was only verified in a desktop harness. Confirm on a real device.

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
