# Product

Where promoted experiments wait to become product. When `/experiment-conclude` renders a **promote**
verdict, the proven piece is parked here — pointing at its evidence — instead of being built on the
spot. Building is a separate, later activity (the product half: `roadmap → spec → design →
implement → reconcile`), which reads these entries and their linked experiments.

Entries accumulate under **milestones**. A milestone is a coherent package worth building as one
unit; keep adding proven pieces until it is, then start the product half. Which milestone an entry
joins is decided with the user at experiment closure.

Rules of the road:
- Only concluded experiments land here; the entry links the one-pager, which owns the full evidence.
  Don't restate the insight log — point at it.
- Each entry carries the *implementation-relevant* distillation: what proved out, the constraints the
  sessions discovered, and where the spike code lives (reference material — building from here is a
  rewrite, or in this project a reconcile-in-place, per the root-spike convention).
- Milestones are numbered and named for the package they add up to. Nothing here is scheduled; order
  within a milestone is not priority (the roadmap decides order).

---

## Milestone 1 — Enqueue-to-audio API (the backend spine)

*The API that turns a public article URL into a private, player-ready read-along audio item — the
foundation Tachikoma pushes to and every web surface will consume. Proven in experiment 001 and, per
graduate-in-place, **already built in place** at root (`api/` + `tts/`, hardened: pydantic-settings,
models/service/schemas/endpoints packages, `APIKeyHeader` auth, pytest/ruff/ty). What remains for
production is **graduation, not construction** — tracked in `BACKLOG.md`.*

- **`enqueue(url, voice?) → eager-generate → pollable item` API shape** — proved in
  [experiment 001](experiments/001-player-ready-item/README.md) (2026-07-17). What proved out: an
  agent `POST`s a URL + API key, the item generates eagerly and becomes pollable, reaching `ready`
  (or `failed`+`error`) — the shape suits an agent client without retry/backoff bookkeeping.
  Implementation-relevant constraints: async-and-poll (`POST` returns immediately, client polls
  `GET`); status lifecycle `generating → ready|failed`; API-key-acts-as-user auth on every route
  including audio; a persisted per-item async handle. Built in place: `api/` — harden here, not
  rebuilt.
- **URL → clean paragraphs (server-side extraction)** — proved in experiment 001 (2026-07-17). What
  proved out: plain `trafilatura` fetch+extract yields trustworthy paragraph splits for typical
  public HTML (clean blog, magazine longread, newsletter, JS-rendered Substack), with a content-type
  clean-fail for non-HTML. Constraints: extraction owns paragraph boundaries; strip edge cruft
  (echoed title, nav labels, footnote glyphs, punctuation-only); non-HTML fails cleanly with a clear
  error; a headless browser is not needed preemptively (reach for it only when a specific site
  fails). Residual: prose-boilerplate stripping (`BACKLOG.md`). Built in place:
  `api/app/service/extract.py`.
- **TTS + per-paragraph read-along timing** — proved in experiment 001 (2026-07-17). What proved out:
  Kokoro-82M on Modal L4 renders paragraphs to Opus with per-paragraph timing; the pause-fold rule
  gives contiguous windows whose last `end` equals audio duration (exact, on real articles); async
  via Modal `spawn()` + lazy `FunctionCall.get(timeout=0)`, no broker. Constraints: TTS is a separate
  deployable (the Modal image is not the app process); return per-paragraph `{index,start,end,text}` +
  `duration` + Opus (WAV fallback); GPU+memory snapshot for ~6s cold start. Built in place:
  `tts/app.py`.
- **The item / read-along contract** — proved in experiment 001 (2026-07-17). What proved out:
  `paragraphs[].{index,start,end,text}` + `duration` + `audio_url` + `status`/`error` matches the
  pre-registered player-read checklist (highlight, seek, progress) with no missing field. Constraints:
  this is the shape the future player consumes; no `words` (word-level deferred). Built in place:
  `api/app/schemas/`.

*Remaining for production (all in `BACKLOG.md`): Postgres + Railway, auth-for-audio graduation,
multi-user quota, API furniture (list endpoint, key CRUD), prose-boilerplate stripping, Random voice.*
