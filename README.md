# Nagara

**Nagara (ながら)**: from *ながら聞き*, consuming content *while doing something else*.

A private, API-first **audio read-later queue**: "Pocket / Instapaper, but for audio." The core operation is `enqueue(url, voice?) → generate eagerly → a private, pollable item that becomes player-ready read-along audio`. An agent client (Tachikoma) pushes reading-list URLs; a future web surface consumes the same API.

The TTS pipeline is proven (Kokoro-82M on Modal L4, ~$0.008/article, paragraph-level read-along timing). The open question is **demand**, and this MVP exists to answer it.

## Repository layout

| Tree | What it is | Stack |
|------|-----------|-------|
| `api/` | The API Worker `nagara-api`: the only routes clients reach (enqueue, poll, retry, audio, images, health), behind a single API key; it writes the item row and creates and restarts the item Workflow | Cloudflare Workers, D1, TypeScript |
| `pipeline/` | The pipeline Worker `nagara`, with no public routes: the item Workflow that does all the work for one item, a DomainQueue Durable Object per domain, the recipe runtime and the Flue author and revision agents | Cloudflare Workers, Workflows, Durable Objects, D1, R2, Flue, Vite |
| `common/` | The package both Workers build from: the shared types, the R2 key layout, presigning, the item row's reads and writes, the D1 migrations and the cassette replay library | TypeScript |
| `tts/` | The GPU text-to-speech service: a separate Modal deployable the item Workflow calls over two web endpoints | Modal, Kokoro-82M, uv (Python 3.12) |
| `web/` | The web surfaces (read-along player, queue, settings) | TanStack Start, *not yet built* |
| `docs/` | How the code works and what nagara is | none |

`api/`, `pipeline/` and `tts/` are **separate deployables**. The TTS code *is* the definition of the GPU image uploaded to Modal, so it cannot run inside a Worker. The item Workflow starts a synthesis over HTTP and asks for its result until it is ready, with no message broker (see [`docs/technical-design/tts-service.md`](docs/technical-design/tts-service.md)). `common/` deploys only its migrations.

## Quick start

The three TypeScript packages share one pnpm workspace: `pnpm install` from the repository root. Locally both Workers keep D1, R2 and the Durable Objects in one shared state folder, `.wrangler-state/`, call the real Firecrawl, AI Gateway and Modal, and receive Modal's audio upload through a quick tunnel and a local proxy. [`docs/technical-design/local-development.md`](docs/technical-design/local-development.md) has the details. To run both Workers locally:

1. Copy `pipeline/.dev.vars.example` and `api/.dev.vars.example` to `.dev.vars` beside them and fill in the secrets.
2. `pnpm migrate:local` in `common/`.
3. `pnpm dev:proxy` in `pipeline/`, then `cloudflared tunnel --no-autoupdate --url http://localhost:8792`, and write the tunnel's `https://<host>/s3` into `R2_UPLOAD_ENDPOINT` in `pipeline/.dev.vars`.
4. `pnpm dev` in `pipeline/` (port 5173), after `.dev.vars` names the tunnel.
5. `pnpm dev` in `api/` (port 8788).
6. `uv run modal serve app.py` in `tts/` for the ephemeral TTS app the local `.dev.vars` points at. It requires Modal credentials in the environment.

Every route but `/health` requires an `X-API-Key` header with the `API_KEY` from `api/.dev.vars`. Enqueue a URL, poll it until `ready`, then follow its audio link:

```sh
curl -X POST localhost:8788/items -H "X-API-Key: $KEY" \
     -H "Content-Type: application/json" -d '{"url": "https://example.com/article"}'
curl localhost:8788/items/<id>           -H "X-API-Key: $KEY"   # poll → queued|generating|ready|failed
curl -L localhost:8788/items/<id>/audio  -H "X-API-Key: $KEY" -o article.ogg
```

**Checks**: `pnpm test` · `pnpm lint` · `pnpm types` in `api/`, `pipeline/` and `common/`; `uv run pytest` · `uv run ruff check` · `uv run ty check` in `tts/`.

## How it works

Enqueue writes the item row as `queued` and creates the item's Workflow instance in the pipeline Worker. The Workflow does all the work in nine steps: it fetches the page through Firecrawl, takes its domain's lease from DomainQueue, runs the domain's recipe (the Flue agents author or revise one when the domain needs it) and derives each unit's spoken form, gives the lease back, acquires the article's images, describes code blocks and unlabelled images with Gemini, starts the synthesis on Modal, waits for it, and stores the timed units with the audio's duration. The item turns `ready` in that last write, or `failed` with the failing step's own error; the poll reads only the row ([`docs/technical-design/item-lifecycle.md`](docs/technical-design/item-lifecycle.md)). Modal uploads the audio to a presigned R2 URL, and the audio route answers with a 307 to a URL signed for one hour. The read-along timing follows the [pause-fold rule](docs/technical-design/read-along-timing.md), so windows are contiguous and end exactly at the audio duration.

## Docs & process

Nagara's engineering knowledge lives in [`docs/`](docs/README.md); the backlog lives in Linear:

- **How the code works**: [`docs/technical-design/`](docs/technical-design/README.md).
- **What nagara is**: [`docs/product-design/`](docs/product-design/README.md).
- **The backlog**: the nagara project in Linear (workspace asermax). Milestones are features, issues are tasks.
- **Conventions** (commands, invariants, code style, work tracking): [`CLAUDE.md`](CLAUDE.md).

## Status

The backend (enqueue, extraction through per-domain recipes, image acquisition and description, TTS, read-along timing, auth) runs on Cloudflare as two Workers on one D1 database and one R2 bucket, with the TTS service on Modal; [`docs/technical-design/`](docs/technical-design/README.md) documents it. The read-along player's shape is proven but not yet built in `web/`; see [`docs/product-design/listening-experience.md`](docs/product-design/listening-experience.md). The agreed build order for what's next (API hardening, the article list, settings, then auth, article creation, and landing) is in [`docs/product-design/what-nagara-is.md`](docs/product-design/what-nagara-is.md).
