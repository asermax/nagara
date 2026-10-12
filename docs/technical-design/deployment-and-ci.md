---
title: "Deployment and CI"
summary: "Three deployables: the API Worker and the pipeline Worker, deployed with wrangler in a fixed order after common/'s D1 migrations, and the TTS service on Modal; each tree runs its own path-filtered CI checks."
created: "2026-07-29"
---

# Deployment and CI

## 🔭 Overview

Nagara ships as three deployables: the API Worker and the pipeline Worker on Cloudflare, and the TTS service on Modal. Each tree runs its own CI checks, path-filtered to its directory. The two Workers deploy with wrangler in a fixed order, after `common/`'s migrations are applied to D1; `tts/` deploys to Modal on its own.

## ☁️ How the Workers deploy

Both Workers deploy with wrangler. Their configurations bind the same D1 database, named `nagara`, and only the pipeline Worker's binds the R2 bucket (see [persistence-and-storage](persistence-and-storage.md)). The API Worker's configuration binds the item Workflow by the pipeline Worker's script name. `nagara.asermax.com` points at the API Worker, the only Worker clients reach.

> [!NOTE] Why the pipeline Worker has no public routes
> The API Worker creates and restarts the item Workflow through the cross-script Workflow binding, and nothing else calls the pipeline. With no route to reach, the pipeline Worker carries no authentication of its own and no edge policy guards it.

`api/` deploys with wrangler from its own configuration, from within `api/` or via CI below; see [item-contract](item-contract.md) for the routes it serves.

`pipeline/` deploys with `pnpm run deploy` (`pnpm deploy` is pnpm's own command and never runs the script), from within `pipeline/` or via CI below; see [item-lifecycle](item-lifecycle.md) for what runs on it. That script builds before it ships: `pnpm build` runs Vite with the Flue and Cloudflare plugins, writing the bundled Worker and a generated `wrangler.json` into `dist/nagara/`, and `wrangler deploy -c dist/nagara/wrangler.json` ships that generated config rather than the hand-written `pipeline/wrangler.jsonc`. The Flue plugin adds the author and revision agents' Durable Object bindings at build time, so the source config alone would ship a Worker without them.

`common/` deploys only its SQL migrations, which drizzle-kit generates from its schema. The Cloudflare workflow's migrate job applies them to D1 with wrangler; see [common-package](common-package.md) for the rest of the package.

> [!NOTE] Why migrations, then the pipeline, then the API
> Both Workers read and write D1, so the schema they build against is applied before either deploys. The API Worker's Workflow binding fails with `workflow.not_found` until the pipeline Worker that holds the item Workflow is deployed, so the pipeline always goes before the API. The binding finds the pipeline by script name when it is called, so a later pipeline deploy reaches the API without redeploying it.

## 🔐 Which secrets each Worker holds

Each Worker holds only the secrets its own calls need.

| Worker | Holds |
|---|---|
| API Worker | the API key, and an R2 API token's S3 key pair it signs GET URLs with |
| pipeline Worker | the Firecrawl key, the AI Gateway token, Modal's proxy auth token, and an R2 API token it signs PUT URLs with |

## 🎙️ How the TTS service deploys

`tts/` is pushed independently with `modal deploy`, from within `tts/` or via CI below; see [tts-service](tts-service.md) for what actually runs on Modal.

## 🔁 CI: path-filtered checks per tree, deploys in a fixed order

```mermaid
flowchart TD
    push(["push to main"]) --> ch["changes:<br/>paths-filter for<br/>common, pipeline, api"]
    ch -->|"common/ changed"| cc["common checks:<br/>test, lint, types,<br/>api and pipeline types,<br/>schema and migrations agree"]
    ch -->|"pipeline/ changed"| pc["pipeline checks:<br/>test, lint, types"]
    ch -->|"api/ changed"| ac["api checks:<br/>test, lint, types"]
    subgraph chain ["deploy chain: a job runs only when no job before it failed"]
        direction TB
        mig["1 migrate, when common/<br/>changed: wrangler d1<br/>migrations apply --remote"]
        pd["2 deploy pipeline, when<br/>pipeline/ changed or 1 ran:<br/>pnpm build, deploy dist config"]
        ad["3 deploy api, when<br/>api/ changed or 1 ran"]
        mig --> pd --> ad
    end
    cc --> mig
    pc --> pd
    ac --> ad
    cc -. "fails" .-> s1(["1, 2 and 3 do not run:<br/>no migration, no<br/>Worker deploys"])
    pc -. "fails" .-> s2(["2 and 3 do not run"])
    ac -. "fails" .-> s3(["3 does not run"])
    tw["tts workflow: test, lint,<br/>types, then modal deploy"]
    push -->|"tts/ changed"| tw
    classDef step fill:#dcfce7,stroke:#16a34a
    classDef broken fill:#fee2e2,stroke:#dc2626
    classDef person fill:#f3f4f6,stroke:#4b5563
    class ch,cc,pc,ac,mig,pd,ad,tw step
    class s1,s2,s3 broken
    class push person
```

Each tree runs **test, lint and types as three parallel jobs** on pushes to `main`, path-filtered to its own directory (`api/**`, `pipeline/**`, `common/**`, `tts/**`), so a docs-only push, or a change to one tree, runs neither another tree's checks nor its deploy. A change to `common/` also runs the type checks of `api/` and `pipeline/` against the changed package, as part of `common/`'s checks. One more `common/` check, `pnpm db:check`, runs drizzle-kit's generate and fails when it leaves a new or changed file under `common/migrations/`, so a schema edit committed without its migration never reaches the migrate job. The `api`, `pipeline` and `common` jobs install with `pnpm install --frozen-lockfile` on Node 24 and run `pnpm test`, `pnpm lint` and `pnpm types`; the `tts` jobs provision the pinned toolchain (uv/ruff/ty/pytest, see the repository's `CLAUDE.md`) with `uv sync --frozen` against `tts/`'s lockfile.

One workflow ships the Cloudflare side with `cloudflare/wrangler-action`. A paths filter decides which of `common/`, `pipeline/` and `api/` changed, and each changed tree's checks run. The deploy chain runs in a fixed order: the migrate job applies `common/`'s SQL migrations to D1 when `common/` changed, the pipeline job runs `pnpm build` and deploys `dist/nagara/wrangler.json` when `pipeline/` changed or the migration ran, and the API job deploys the API Worker when `api/` changed or the migration ran, after the pipeline deploy when that one runs. A `common/` change therefore redeploys both Workers, which compile it in, and a push that changes only `pipeline/` deploys only the pipeline. A job in the chain runs only when no job before it failed. A job skipped because its tree did not change does not stop the jobs after it. A failed `common/` check, the schema check included, stops all three: no migration, no pipeline deploy and no API deploy. A failed `pipeline/` check stops both Worker deploys, and a failed `api/` check stops the API deploy. The jobs authenticate with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. `tts` keeps its own workflow, with a **`deploy` job that depends on all three of its checks**, runs `modal deploy` and authenticates with `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET`. All four are GitHub Actions secrets.

> [!NOTE] Why one workflow for the Cloudflare side
> The deploys depend on each other: the migrations go first and the API Worker last. Jobs in one workflow wait on each other within a push.

> [!TIP] Rejected: one workflow per tree
> Separate workflows cannot wait on each other within a push without polling one another, so the pipeline and API deploys could not wait for the migrations.

> [!WARNING] Two migration runs at once are not guarded
> Nothing serializes two runs of the Cloudflare workflow, so two pushes to `main` in quick succession can apply `common/`'s migrations twice at the same time. The chain relies on deploys never being made twice in quick succession.

The `tts` check jobs install the full dev dependency group (torch-cpu, kokoro, numpy) because `ty` needs them to resolve `app.py`'s image-runtime imports locally; the deploy job installs only the Modal client (`--no-dev`). uv's lockfile-keyed cache absorbs most of the repeat install cost.

## 📦 What binaries the repository accepts

Audio and images are handled differently.

**Audio is ignored outright.** `.gitignore` covers `*.ogg`, `*.wav`, `*.mp3`, `*.m4a`, `*.opus` and `*.flac`, so no audio file can be staged by accident. Every audio file here is output of the TTS pipeline: regenerable for roughly $0.008 an article (see [tts-service](tts-service.md)) and megabytes each, so there is no audio artifact worth the space, and LFS would only make an unwanted commit cheaper rather than preventing it. A test that needs audio generates it into a working directory the ignore already covers.

**Images go through Git LFS.** `.gitattributes` routes `*.png`, `*.jpg`, `*.jpeg` and `*.webp` as LFS pointers, because `web/` will carry real assets that have to be checked in, and a pointer keeps the bytes out of the packfile every clone downloads.

> [!WARNING] A binary committed as a plain blob is permanent until someone rewrites history
> Deleting the file in a later commit removes it from the working tree and leaves the blob in every clone at full size. Two Opus fixtures, 9.35 MB together, reached pushed history this way, and getting them back out took a `filter-repo` rewrite and a force push over a shared branch: `.git` dropped from 12 MB to 672 KB, but the remote still serves each unreachable blob by hash afterwards, because rewriting history does not reach objects already distributed to other clones and caches.

## ⏩ What is not built yet

`web/` and `api/` are served from separate hosts today; serving them from one origin once `web/` exists is not built.

A Worker deploy that lands while item Workflow instances are running is not handled; a deploy can run a step again, and the item Workflow accepts that for synthesis (see [item-lifecycle](item-lifecycle.md)).

---

Related: [tts-service](tts-service.md) · [item-lifecycle](item-lifecycle.md) · [common-package](common-package.md) · [local-development](local-development.md) · [persistence-and-storage](persistence-and-storage.md) · [authentication](authentication.md) · [invariants](invariants.md)
