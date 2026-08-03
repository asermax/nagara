# Nagara

**Nagara (ながら)**: from *ながら聞き*, consuming content *while doing something else*.

A private, API-first **audio read-later queue**: "Pocket / Instapaper, but for audio." The core
primitive is `enqueue(url, voice?) → generate eagerly → a private, pollable item that becomes
player-ready read-along audio`. An agent client (Tachikoma) pushes reading-list URLs; a future web
surface consumes the same API.

The TTS pipeline is proven (Kokoro-82M on Modal L4, ~$0.008/article, paragraph-level read-along
timing). The open question is **demand**: this MVP exists to find out.

## Repository layout

| Tree | What it is | Stack |
|------|-----------|-------|
| `api/` | The queue API: enqueue, poll, audio delivery; single-key auth; SQLite/Postgres persistence | FastAPI, SQLAlchemy, uv (Python 3.12) |
| `tts/` | The GPU text-to-speech service: a **separate Modal deployable** the API invokes remotely | Modal, Kokoro-82M, uv (Python 3.12) |
| `web/` | The web surfaces (read-along player, queue, settings) | TanStack Start, *not yet built* |
| `docs/` | An Obsidian vault: how the code works, what nagara is, and the quest log | none |

`api/` and `tts/` are **separate deployables**: the TTS code *is* the definition of the GPU image
uploaded to Modal, so it cannot run inside the API process. The API invokes it remotely with Modal's
own spawn/poll primitives, no message broker (see
[`docs/technical-design/tts-service.md`](docs/technical-design/tts-service.md)).

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

Enqueue creates the item as `generating`, extracts the URL into aligned display and spoken paragraph
lists ([`docs/technical-design/article-extraction.md`](docs/technical-design/article-extraction.md)),
spawns a remote synthesis call, persists its handle, and returns immediately. Polling resolves the call
lazily: *still running* stays `generating`, a *crash* becomes `failed` with the error, *done* stores
the audio and per-paragraph timing and becomes `ready`. The read-along timing follows the
[pause-fold rule](docs/technical-design/read-along-timing.md) so windows are contiguous and end exactly
at the audio duration.

## Docs & process

Nagara's engineering knowledge and its process both live in [`docs/`](docs/README.md), an Obsidian
vault:

- **How the code works**: [`docs/technical-design/`](docs/technical-design/README.md).
- **What nagara is**: [`docs/product-design/`](docs/product-design/README.md).
- **The backlog** (journeys and raids, and the quests under them) and how work moves through it:
  [`docs/quest-log/README.md`](docs/quest-log/README.md).
- **Conventions** (commands, invariants, code style, spike location): [`CLAUDE.md`](CLAUDE.md).

## Status

The backend spine (enqueue, extraction, TTS, read-along timing, auth) is built and documented in
[`docs/technical-design/`](docs/technical-design/README.md). Markdown-formatted paragraphs are built
on top of it. The read-along player's shape is proven but not yet built in `web/`; see
[`docs/product-design/listening-experience.md`](docs/product-design/listening-experience.md). The
agreed build order for what's next (API hardening, the article list, settings, then auth, article
creation, and landing) is in [`docs/product-design/what-nagara-is.md`](docs/product-design/what-nagara-is.md).
