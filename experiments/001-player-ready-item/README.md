# 001 — Slice 1: does a real push yield a player-ready item?

**Question**: Does slice-1 — `enqueue(url) → eager-generate → pollable item` — produce a
**player-ready** item (a paragraph split I'd trust + Opus audio + a clean status/failure lifecycle)
from a real Tachikoma push? Extraction quality is a **first-class part of the answer**, not a given —
if URL→paragraphs can't be made trustworthy here, that is itself the result, and it routes to its own
experiment.

**Hypothesis**: Slice-1 as specced produces player-ready items. An agent `POST`s a URL with its API
key; extraction yields clean paragraphs; the item generates eagerly (Modal `spawn()`) and reaches
`ready` with Opus audio and paragraph boundaries that match the article; inputs that can't be fetched
surface as `failed` + `error`. It is **disproven** if any of these is observed:

1. a *fetchable* fixture's returned `paragraphs[]` merge, fragment, or garble the article's real
   structure (I reject the split);
2. the item shape is missing a field the player's read operations need — checked against a
   pre-registered checklist: paragraph highlight needs per-paragraph `[start, end)` + `text`,
   click-to-seek needs `start`, a progress bar needs `duration`;
3. the async-and-poll interaction forces the client into retry/backoff/timeout bookkeeping that a
   block-until-ready call would eliminate, **or** polling can't distinguish `generating` from a
   silently-dead job;
4. a forced Modal-side crash lands `ready` (or `failed` with an empty `error`) instead of `failed`
   with a populated `error`.

**Judging** — two lenses, judged against **real articles from the Tachikoma reading list** (real
fetch, real Kokoro synthesis), not toy text:

| Fixture | Type | What it stresses |
|---|---|---|
| [My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey) | clean static blog | the easy case — semantic HTML |
| [Could an LLM Be Conscious?](https://www.bostonreview.net/articles/could-a-large-language-model-be-conscious/) | magazine longread | standard article markup |
| [Revisiting No Silver Bullets…](https://newsletter.pragmaticengineer.com/p/revisiting-no-silver-bullets-in-the) | newsletter | long-form, mixed structure |
| [The 80% Problem in Agentic Coding](https://addyo.substack.com/p/the-80-problem-in-agentic-coding) | Substack | JS-rendered — expected to break naive fetch |
| [Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) | PDF | a fetchable URL that isn't HTML |

- **Task criterion** (concrete, checkable):
  1. Each fixture pushed via `POST /items` (API key) reaches a terminal state — `ready` with playable
     audio (Opus, WAV fallback if the codec path snags), *or* `failed` with a clear `error`. For
     `ready` items, paragraph timing is monotonic, non-overlapping, and contiguous, with the final
     `end` ≈ audio duration.
  2. **Paragraph-split quality** — on the fetchable articles, I validate that paragraph boundaries
     match the real article structure (no merged, fragmented, or garbage paragraphs). The load-bearing
     acceptance check.
  3. A forced Modal-side failure surfaces as `status: failed` + a populated `error` (the
     `FunctionCall.get()` re-raise probe — the one unverified mechanism the `failed` path depends on).
  4. **Item-shape checklist** — a `ready` item is scored against the player's actual read operations:
     `paragraphs[].{start,end,text}` present and correct for highlight, `start` for seek, `duration`
     for progress. A missing/wrong field fails this.
- **Insight criterion**: Where did the real articles put the boundary between "clean-HTML extraction
  is enough" and "needs a headless browser"? Did driving it as the agent confirm async-and-poll is the
  right interaction (per the named observables in disproof #3), or surface a better shape? Did the item
  shape carry everything a player needs, or did the checklist expose a gap?
- **Kill / timebox**: ≤ 3 focused sessions, **build time inside the box** — a from-scratch FastAPI +
  SQLite + extraction + Modal spawn/lazy-`get` build is real work, and if it eats the box before the
  shape questions get exercised, that overrun is itself a signal. If paragraph quality can't be made
  trustworthy on *clean HTML* within the box, the finding is that URL→paragraphs extraction is a
  distinct hard problem: route it to its own experiment and record that slice-1-as-specced does not yet
  yield player-ready items.

## Setup

**What gets built** (the cheapest thing that answers the question — everything the judging doesn't
test is hardcoded or seeded, nothing more). Three modules, each mapped to a judging criterion.
`api/` is managed with **uv**, pinned to **Python 3.12** (Kokoro/`modal`-client constraints; system
Python is 3.14).

- **`api/` store + poll** (FastAPI, spike-at-root): `POST /items {url, voice?}`, `GET /items/{id}`
  (the poll target), `GET /items/{id}/audio`. Auth via `X-API-Key` — **one seeded key in env = the
  single user**. **SQLite** for items (incl. the persisted Modal `call_id`); audio stored as a local
  file and served from `/audio`. *No quota, no list endpoint* — neither is exercised by the question;
  they join the later API-hardening pass (captured in `BACKLOG.md`). (Production target is Railway +
  Postgres — a graduation concern, not built here.)
- **`api/` extraction**, *before* the TTS spawn — fetch the URL with `requests` + **trafilatura** and
  split into clean `paragraphs[]`. **Basic fetch first**; reach for a headless browser (playwright)
  only if a *fetchable HTML* fixture comes out bad mid-session. **Non-HTML (the PDF) clean-fails** —
  detected by content-type, lands `failed` with a clear error rather than being force-parsed into
  garbage. Paragraph boundaries are our responsibility, and their quality is the load-bearing check.
- **`tts/`** (Modal, separate `modal deploy`): **adapted from the existing working service**
  (`~/Downloads/kokoro-tts/modal_kokoro.py` + the proven per-paragraph timing of `test_paragraphs.py`)
  — the `Kokoro` L4 class, changed to accept `paragraphs[]` and return per-paragraph
  `{index, start, end, text}` timing + audio + `duration`. **No `words`** (out of scope).
  **Memory + GPU snapshot enabled** (`enable_memory_snapshot` + `enable_gpu_snapshot`, ~27s→~6s cold
  start) — the alpha GPU-snapshot is user-validated as working, so it's in rather than deferred.
  - **Timing rule** (the reference gives durations, not cumulative bounds — this defines them):
    each paragraph window is `[start, start + dur + inter_paragraph_pause)`; the pause is folded into
    the *preceding* paragraph's `end`, so windows are contiguous and the last `end` == total audio
    `duration`. No dead highlight zone during pauses.
  - **Audio format**: Opus (a 20-min WAV base64'd in the Modal return is ~73MB; Opus ~4MB). The
    libopus/ffmpeg codec path in the image is a **named build risk** — if it snags, fall back to WAV
    (what the reference already emits); "playable audio" is the only judged property either way.
  - **Failure probe hook**: a reserved `voice="__raise__"` makes the deployed Modal function raise,
    so the exception genuinely round-trips through `FunctionCall.get()` (task #2's real path, not a
    pre-spawn raise in `api/`).
- **Eager generation**: on `POST`, extract → `spawn(...)` the deployed Modal function →
  persist the call id with `status=generating`. `GET /items/{id}` resolves lazily via
  `FunctionCall.from_id(call_id).get(timeout=0)` — no broker, no worker process. (Exact spawn-from-a-
  class handle — `Cls.from_name` vs `Function.from_name` — is verified during build, before the
  judged sessions.)

**Item shape** (returned by `GET /items/{id}`):

```jsonc
{
  "id": "itm_a1b2c3",
  "url": "https://mitchellh.com/writing/my-ai-adoption-journey",
  "title": "My AI Adoption Journey",
  "status": "generating | ready | failed",   // eager gen: generating from first observation
  "voice": "af_heart",                        // hardcoded default for the spike; voice? passes through
  "created_at": "2026-07-17T12:00:00Z",
  "duration": 512.3,                          // seconds, once ready
  "audio_url": "/items/itm_a1b2c3/audio",
  "paragraphs": [                             // read-along timing — consumed by a future player as-is
    { "index": 0, "start": 0.0, "end": 28.3, "text": "…" }
  ],
  "error": null                               // populated when status=failed
}
```

*(The MVP's full `queued → generating → ready` lifecycle returns once a non-eager path exists; under
eager generation the item is `generating` from the client's first observation, so `queued` is omitted
here rather than faked.)*

**Session protocol** (scorable tasks interleaved with reflection):

1. **Push all 5 fixtures.** Record each item's terminal status; play the audio; I validate
   paragraph-split quality on the fetchable ones; score one `ready` item against the item-shape
   checklist. → *reflect*: where did extraction break — and is the HTML-vs-headless boundary a clean
   line or a mess?
2. **Force a Modal-side error** — push an item with the sentinel `voice="__raise__"` so the deployed
   Modal function raises and the exception round-trips through `FunctionCall.get()`. Confirm the item
   lands `failed` with a populated `error`, and that a still-running poll (`TimeoutError`) is
   distinguishable from this dead-job re-raise. → *reflect*: does `.get()` surface errors cleanly; is
   the failure shape right?
3. **Drive it exactly as Tachikoma would** — push via key, poll `GET /items/{id}` until `ready`, then
   read audio + paragraphs the way the player will. → *reflect*: does async-and-poll avoid client-side
   retry/backoff bookkeeping and cleanly tell `generating` from a dead job; does the item shape drop
   into a player with zero reshaping?

**Spike location**: root `api/` (FastAPI) + `tts/` (Modal service), per the spike-at-root convention
in `CLAUDE.md`. Hardened in place if it proves out; no isolated sandbox.

## Notes

*(insight log — appended live during `/experiment-run`)*

**2026-07-17 — pre-session probe: mechanism verified.** `nagara-tts` deployed to Modal (150s build,
model + spacy baked). Probe through the real api client:
- **Real synth** → `ready`, `audio/ogg`, duration 4.88s, contiguous windows `[(0, 0.0, 2.5), (1, 2.5,
  4.88)]`, **last end == duration** ✓. Crucially `saw 'generating' while running: True` — a running
  job returns `generating` (the `TimeoutError` path holds); it is *not* misclassified as failed.
- **`voice="__raise__"`** → `FunctionCall.get()` re-raised the remote exception; item landed `failed`
  with `RuntimeError: forced failure…` ✓.
- All three "only building answers" unknowns resolved positively (spawn handle · real roundtrip +
  timing rule · the `get()` re-raise the `failed` path depends on). No mechanism bug — cleared to run
  the judged sessions.
- GPU+memory snapshot later enabled (user had already validated the alpha feature works) and
  re-verified: identical clean probe (ready + timing, and `__raise__` → failed).

**2026-07-17 — verdict inputs accepted + cleanup.** User validated **split quality: good** and
**audio: "fantastic"** — task #2 (the load-bearing check) and the audio half of task #1 pass. Fixes
applied post-validation:
- Extraction now post-processes paragraphs — drops the echoed title, nav labels (`Table of
  Contents`), footnote glyphs (`↩`), and punctuation-only artifacts. Verified on all 4 HTML fixtures:
  title echo gone, zero residual dash/ToC/footnote cruft (clean-blog 68→60 paras).
- **Residual:** prose boilerplate (footer donation, sponsor aside) is *not* stripped — full-sentence
  cruft a generic filter would risk over-trimming; backlogged for a dedicated pass.
- Cleared the `__raise__` failure-probe sentinel from `tts/app.py` (redeployed) and removed the probe
  script — the `get()` re-raise path is validated, the backdoor is no longer wanted in the service.
- Dropped the `requests` dependency: extraction now fetches via `trafilatura.fetch_response`
  (`with_headers=True`), which supplies both the decoded HTML and the content-type header the non-HTML
  clean-fail needs. Re-verified on all 5 fixtures — identical results (4 HTML fetch+extract the same,
  incl. Substack/bostonreview on trafilatura's default UA; PDF still clean-fails). One fewer dep.
- **Item-shape checklist (task #4) scored** against the substack `ready` item: `paragraphs[].{start,
  end, text}` present (highlight), `start` present (seek), `duration` present (progress), `audio_url`
  present — no missing or wrong field. Criterion met.
- **Process note:** under graduate-in-place, this experiment absorbed substantial production-hardening
  *inside* the timebox (pydantic-settings, module packages, `APIKeyHeader` auth on all routes, ~17
  tests, ruff/ty, a dropped dependency). Expected for this project — but a signal that "spike" here
  means near-production code, so future experiment timeboxes should budget build effort accordingly.

**2026-07-17 — session 1 (5 fixtures, full API) + real-HTTP.** Pushed all 5 real reading-list
articles through the API (extract → spawn → poll → store), audio + splits saved to
`api/data/fixtures/`.
- **Outcomes:** 4/4 HTML → `ready` (clean-blog 68 paras/876s · magazine 132/2945s · newsletter
  77/1303s · substack-js 142/1553s); **PDF → `failed` at POST** (`unsupported content-type
  'application/pdf'`) — the designed clean-fail.
- **HTML-vs-headless boundary insight:** basic `requests`+trafilatura handled *all four* HTML
  fixtures, **including the JS-heavy Substack** (Substack server-renders the post). The headless
  browser wasn't needed for any fixture in this set — the boundary sits further out than expected.
- **Split-quality wrinkles (consistent, edge-only):** title echoed as para[0] in 3/4; nav/boilerplate
  cruft — "Table of Contents", a lone "-", a footer donation paragraph, a sponsor aside, footnote "↩"
  markers. Article *bodies* are cleanly segmented. *(Awaiting the user's split-quality judgment — task
  #2, the load-bearing check. Magazine = 49 min audio; plausible for a long essay, to confirm on
  listen.)*
- **Real-HTTP (uvicorn + curl):** auth 401 without key · POST 202 · poll→`failed` (`__raise__`) over
  HTTP · `GET /audio` streamed 4.29 MB Opus (`content-type: audio/ogg`). API verified as a running
  HTTP server, not just via TestClient.
- *(The `api/` spike was subsequently restructured — pydantic-settings, models/service/schemas/
  endpoints packages, APIKeyHeader auth on all routes incl. audio. Structure only; behavior unchanged,
  16 unit tests + ruff + ty green. Spike evidence above stands.)*

**2026-07-17 — build snapshot (pre-session).**
- **Built:** `tts/app.py` (Modal `nagara-tts` / `Kokoro` L4, adapted from the reference — per-paragraph
  timing with the pause-fold rule, Opus w/ WAV fallback, `voice="__raise__"` failure sentinel; no
  GPU-snapshot). `api/` (uv, Python 3.12): FastAPI `POST /items` · `GET /items/{id}` · `GET
  /items/{id}/audio`; SQLAlchemy `Item` model on SQLite; `X-API-Key`; live `requests`+`trafilatura`
  extraction with non-HTML clean-fail; Modal `spawn` + lazy `FunctionCall.get(timeout=0)` poll.
- **Verified (no Modal):** api imports + all 3 routes; `tts/app.py` structure (`nagara-tts` app,
  `Kokoro` class); ruff clean both packages; **live extraction on the clean fixture** (mitchellh.com)
  → 68 paragraphs + title; **pytest green — 20 tests** (api 15: extract / tts-client / routes;
  tts 5: `build_timeline` contiguity + last-end == duration). Timing rule extracted to a pure
  `build_timeline` for testability.
- **Early extraction wrinkles to watch** (the split-quality lens): on mitchellh.com the first
  "paragraph" is the title echoed, and the last carries a footnote `↩`. Real, minor — flagged for the
  quality judgment, not fixed pre-emptively.
- **Pending — needs a live Modal deploy** (the "only building answers" unknowns): does `modal deploy`
  succeed from this env; is `Cls.from_name(...).synthesize.spawn()` the right handle; and the
  load-bearing probe — does `FunctionCall.get(timeout=0)` raise **`TimeoutError`** while running and
  **re-raise** the remote exception on a `__raise__` crash (vs. some other exception type that would
  misclassify a running job as failed). Verified before the judged sessions.

## Verdict

**PROMOTE.** Slice-1 produces player-ready items from a real push. All four pre-registered task
criteria met, and none of the four disproof conditions triggered: 4/4 HTML fixtures reached `ready`
with playable Opus audio and monotonic, contiguous paragraph timing (last `end` == duration); the PDF
clean-failed with a clear content-type error; paragraph-split quality was validated good (then
improved); the item shape carried every field a read-along player reads (`paragraphs[].{start, end,
text}` + `duration`, checklist scored against a `ready` item); and a forced Modal-side crash surfaced
as `failed` + populated `error` (probe
and real-HTTP), while a running job was never mis-flagged.

The insight lens paid off: **basic `trafilatura` fetch handled every HTML fixture, including the
JS-rendered Substack** (server-rendered) — the headless-browser escalation the setup staged was never
needed, so the HTML↔headless boundary sits further out than assumed. The zero-broker Modal `spawn()` +
lazy `get(timeout=0)` async held in practice, and the pause-fold timing rule reconciled exactly with
audio duration on real articles. The kill-branch ("if extraction can't be trusted on clean HTML, route
it to its own experiment") did **not** fire — extraction came in good; only prose-boilerplate stripping
remains, captured in `BACKLOG.md`, not blocking.

**Scope:** self-use, on Nagara only; one session against 5 real articles from the owner's own reading
list; single-user spike (one seeded key, no quota/multi-user). Establishes the pipeline produces
player-ready items for typical public HTML articles. Does **not** establish demand, generalization
beyond these article types/sites, or multi-user behavior.

**Decision:** promote the proven pieces to `PRODUCT.md` (Milestone 1 — the backend spine). Follow-ups
routed to `BACKLOG.md`: prose-boilerplate stripping, auth-for-audio graduation, Postgres/Railway, API
furniture (quota, list, key CRUD), Random voice. The spike code stays at root and is **hardened in
place** from the product backlog (per the graduate-in-place convention), not rebuilt.
