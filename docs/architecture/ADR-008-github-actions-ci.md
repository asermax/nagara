# ADR-008 — GitHub Actions CI for both subprojects; tts deploys to Modal on main

**Status**: Accepted **Date**: 2026-07-18 **Grounded in**: — **Related**: [ADR-001](ADR-001-modal-tts-zero-broker-async.md), [ADR-005](ADR-005-python-toolchain.md), [ADR-006](ADR-006-railway-deployment.md)

## Context

The monorepo holds two independently deployable Python subprojects — `api/` and `tts/` — that share a uv/ruff/ty/pytest toolchain (ADR-005) but ship on different paths: `api/` auto-deploys to Railway from its connected GitHub source (ADR-006), while `tts/` is a separate Modal deployable pushed with `modal deploy` (ADR-001). Nothing currently gates a change on its checks passing, and the tts deploy is manual. Both need automated quality gates on every change, and the tts deploy should run itself once those gates pass.

## Decision

Each subproject gets its own GitHub Actions workflow (`.github/workflows/api.yml`, `.github/workflows/tts.yml`), **path-filtered** to its own directory so a change to one (or to docs) does not trigger the other — the same isolation principle as Railway's watch paths (ADR-006). Both run on **pushes to `main`**.

Each workflow runs **three checks as separate parallel jobs** — test (`pytest`), lint (`ruff check`), and types (`ty check`) — each provisioning the environment with the pinned toolchain via `uv sync --frozen` against the subproject's lockfile.

The `tts` workflow adds a **`deploy` job that depends on all three checks** and runs `modal deploy`. Since the workflow only triggers on pushes to `main`, no extra branch guard is needed. It authenticates to Modal with `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` supplied as repository secrets. `api` has no deploy job: Railway owns that deploy on push to `main`.

## Consequences

- **Independent, path-scoped pipelines**: an api-only change runs only api checks and vice versa; docs-only pushes run neither. Cheaper runs and clearer signal, at the cost of two workflow files to keep in step rather than one.
- **tts ships on green**: a push to `main` touching `tts/**` deploys to Modal only after test, lint, and types all pass — the previously manual `modal deploy` becomes automatic and gated.
- **Two deploy models coexist by design**: api deploys via Railway's own GitHub integration (outside Actions), tts deploys from within Actions. CI does not gate the Railway deploy; that remains Railway's concern (ADR-006).
- **New required secret surface**: `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` must exist as GitHub Actions secrets, or the tts deploy job fails. These are the same credentials used for a local `modal deploy`.
- **Type-checking cost in tts CI**: the tts check jobs install the full dev group (torch-cpu, kokoro, numpy) because `ty` needs them to resolve `app.py`'s image-runtime imports (ADR-005); the deploy job installs only the modal client. uv's cache keyed on the lockfile absorbs most of the repeat cost.

## Alternatives considered and not chosen

- **A single workflow covering both subprojects** — not chosen: it couples two independent deployables into one run and one failure surface, and complicates path filtering and the tts-only deploy gate.
- **One combined check job running all three tools sequentially** — not chosen: parallel per-check jobs give faster feedback and a precise failed-signal (which of test/lint/types broke) at negligible extra cost.
- **Deploying tts to Modal from a Railway-style external integration** — not chosen: Modal has no equivalent push-to-deploy GitHub source, and running `modal deploy` inside the gated Actions job keeps the deploy behind the checks.
- **Gating the api Railway deploy on CI** — not chosen: Railway deploys from its own connected source; wiring Actions to block it adds coordination for no current benefit on a single-service MVP.
