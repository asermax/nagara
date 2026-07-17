# Nagara

**Nagara (ながら)** — from *ながら聞き*, consuming content *while doing something else*.

A private, API-first **audio read-later queue** — "Pocket / Instapaper, but for audio." The core
primitive is `enqueue(url, voice?) → generate eagerly → a private, pollable item that becomes
player-ready read-along audio`. An agent client ([Tachikoma](../../shin-sekai/01_Projects/tachikoma/README.md))
pushes reading-list URLs; a future web surface consumes the same API.

The TTS pipeline is proven (Kokoro-82M on Modal L4, ~$0.008/article, paragraph-level read-along
timing). The open question is **demand** — this MVP exists to find out.

## Repository layout

| Tree | What it is | Stack |
|------|-----------|-------|
| `api/` | The queue API — enqueue, poll, audio delivery; single-key auth; SQLite persistence | FastAPI, SQLAlchemy, uv (Python 3.12) |
| `tts/` | The GPU text-to-speech service — a **separate Modal deployable** the API invokes remotely | Modal, Kokoro-82M, uv (Python 3.12) |
| `web/` | The web surfaces (read-along player, queue, settings) | TanStack Start — *not yet built* |

`api/` and `tts/` are **separate deployables**: the TTS code *is* the definition of the GPU image
uploaded to Modal, so it cannot run inside the API process. The API invokes it remotely with Modal's
own spawn/poll primitives — no message broker (see
[ADR-001](docs/architecture/ADR-001-modal-tts-zero-broker-async.md)).

## Quick start

**API** (from `api/`):

```sh
uv sync
uv run uvicorn app.main:app --reload
```

Every route requires an `X-API-Key` header (the key acts as the user; default is a dev key,
overridable via `NAGARA_API_KEY`). Enqueue a URL, poll it until `ready`, then fetch its audio:

```sh
curl -X POST localhost:8000/items -H "X-API-Key: dev-key-nagara" \
     -H "Content-Type: application/json" -d '{"url": "https://example.com/article"}'
curl localhost:8000/items/<id>        -H "X-API-Key: dev-key-nagara"   # poll → generating|ready|failed
curl localhost:8000/items/<id>/audio  -H "X-API-Key: dev-key-nagara" -o article.ogg
```

**TTS service** (from `tts/`): `uv run modal serve app.py` (dev) or `uv run modal deploy app.py`
(prod). Requires Modal credentials in the environment.

**Checks** (both trees): `uv run pytest` · `uv run ruff check` · `uv run ty check`.

## How it works

Enqueue creates the item as `generating`, extracts the URL into clean paragraphs
([trafilatura](docs/architecture/ADR-004-trafilatura-extraction-headless-deferred.md)), spawns a
remote synthesis call, persists its handle, and returns immediately. Polling resolves the call
lazily — *still running* stays `generating`, a *crash* becomes `failed` with the error, *done*
stores the audio + per-paragraph timing and becomes `ready`. The read-along timing follows the
[pause-fold rule](docs/design/DES-001-read-along-timing-windows.md) so windows are contiguous and end
exactly at the audio duration.

## Docs & process

Nagara is developed with the [zenku](../../claude-plugins/zenku) experiment-driven workflow.

- **What / why / how**: [`docs/`](docs/README.md) — feature specs, designs, and the ADR/DES decision
  records. Milestone 1 (the backend spine) is fully documented there.
- **Experiments**: [`experiments/`](experiments/README.md) — pre-registered one-pagers; the backend
  spine was proven in [experiment 001](experiments/001-player-ready-item/README.md).
- **What's proven, what's next**: [`PRODUCT.md`](PRODUCT.md) · [`BACKLOG.md`](BACKLOG.md) ·
  [`LEARNINGS.md`](LEARNINGS.md).
- **Conventions** (build/test/lint, spike location): the `## zenku` section of
  [`CLAUDE.md`](CLAUDE.md).

## Status

Milestone 1 — the enqueue-to-audio backend spine — is built and documented. Deferred to the backlog:
Postgres + Railway graduation, browser-friendly audio auth, multi-user + quota, a list endpoint and
API-key CRUD, prose-boilerplate stripping, and Random voice. The `web/` surfaces are next.
