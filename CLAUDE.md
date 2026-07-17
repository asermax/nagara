# Nagara

**Nagara (ながら)** — from *ながら聞き*, consuming content *while doing something else*.

A private, API-first **audio read-later queue** — "Pocket / Instapaper, but for audio." Core
primitive: `enqueue(url, voice?) → generate eagerly → private item in your queue with a listen
link`. The web paste-and-listen page is the front door; the queue-for-later (with an API so
[Tachikoma](../../shin-sekai/01_Projects/tachikoma/README.md) can push reading-list items) is the
real objective.

The TTS pipeline is already proven (Kokoro-82M on Modal L4, ~$0.008/article, paragraph-level
read-along timing solved). The open gate is **demand** — does anyone want this? The MVP exists to
find out. Full idea + MVP spec: `../../shin-sekai/02_Areas/Ideas/audio-article-product/`.

## Stack

- **`web/`** — TanStack Start (TS/React), Panda-CSS, react-query. The 5 MVP pages.
- **`api/`** — FastAPI (Python, managed with **uv**). The queue + single-key auth (quota and
  API-key CRUD are deferred furniture, not yet built). Invokes the TTS service **remotely via Modal**
  (spawn + lazy `FunctionCall.get` poll, zero broker — see
  [ADR-001](docs/architecture/ADR-001-modal-tts-zero-broker-async.md)), not over HTTP. Production
  target is **Railway + Postgres**; the current spike uses **SQLite** (Postgres is a graduation
  concern — [ADR-003](docs/architecture/ADR-003-sqlalchemy-sqlite-to-postgres.md)).
- **`tts/`** — Modal service running Kokoro-82M (its own `modal deploy`). It is a **separate
  deployable**, not part of `api/`: Modal code *is* the image definition uploaded to Modal, so it
  cannot live inside the FastAPI process. `api/` invokes it remotely.

## zenku

- **Purpose**: Validate demand for a private, API-first audio read-later queue by productizing
  Tachikoma's existing TTS pipeline into a shippable MVP. The tech is de-risked; what's unproven is
  the product *shape* and whether there's an audience.
- **Spike location**: **Spike-at-root, graduate in place.** Experiment spikes are built directly in
  root `web/` and `api/` (thin at first, hardened as the shape proves out), *not* in an isolated
  `experiments/NNN/spike/` sandbox. Each `experiments/NNN-slug/README.md` one-pager pre-registers
  the question and points at the root code it exercises. This is a deliberate deviation from
  zenku's throwaway-spike default, chosen because the technical risk is already spent and a full
  rewrite would be wasted motion — accept that early shortcuts in the root tree are tech debt to
  reconcile later, not a separate sandbox to discard.
- **Run a spike**: `web/` → `pnpm dev`. `api/` → `uv run uvicorn app.main:app --reload`. `tts/` →
  `uv run modal serve` (dev) / `uv run modal deploy` (prod), from within `tts/`. Both `api/` and
  `tts/` are pinned to **Python 3.12** (Kokoro/`modal` client constraints; the system Python is 3.14).
- **Build / test / lint**:
  - `web/` → build `pnpm build` · test `pnpm test` (Vitest) · lint/format `pnpm biome check`
  - `api/` & `tts/` → test `uv run pytest` · lint `uv run ruff check` · types `uv run ty check`
    (uv-managed; `ruff` / `ty` / `pytest` are dev deps). Payloads modeled with **pydantic**. `tts/`
    carries the Modal-image runtime deps (kokoro/torch-cpu/numpy/soundfile) as **dev** deps so `ty`
    can type-check all of `app.py` locally.
- **Docs layout**: framework-core default map (no deviations). Milestone 1 (the backend spine) is
  documented under `docs/` — see [`docs/feature-specs/enqueue-to-audio-api.md`](docs/feature-specs/enqueue-to-audio-api.md),
  its [design](docs/feature-designs/enqueue-to-audio-api.md), and ADR-001…005 / DES-001. The
  toolchain choice itself is recorded in [ADR-005](docs/architecture/ADR-005-python-toolchain.md).
