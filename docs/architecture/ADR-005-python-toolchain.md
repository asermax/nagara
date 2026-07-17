# ADR-005 — Python toolchain: uv, ruff, ty, pytest

**Status**: Accepted **Date**: 2026-07-17

## Context

Both Python deployables — the API (`api/`) and the TTS service (`tts/`) — need a consistent, project-wide standard for dependency management, linting, formatting, type checking, and testing. A shared toolchain keeps the two trees interchangeable to work in and lets the same commands run in both. Both are pinned to Python 3.12 (a Kokoro / Modal-client constraint; the system Python is newer).

The project's usual Python default elsewhere is Poetry; this project deliberately reconsiders that for a faster, single-vendor stack.

## Decision

We standardize both Python packages on:

- **uv** — dependency management and virtual environments (the lockfile is committed; the venv is not).
- **ruff** — linting and formatting.
- **ty** — type checking.
- **pytest** — tests.

`ruff`, `ty`, and `pytest` are dev dependencies of each package. `ty` type-checks all code, which requires that even the TTS image's runtime libraries (the model, audio, and array stack) be present as **dev dependencies** of `tts/` so the service code type-checks locally, independent of the deployed image. Payloads crossing service boundaries are modeled with pydantic so they validate and type-check end to end.

The concrete commands live in `CLAUDE.md` (the project's zenku conventions) and each `pyproject.toml`; this record captures only the *choice* of tools.

## Consequences

- **One toolchain across both trees**: identical lint/type/test invocations in `api/` and `tts/`; no per-package divergence to remember.
- The Astral trio (uv/ruff/ty) is **fast and single-vendor**, reducing config surface and cross-tool friction.
- `ty` is comparatively young; a type-check gap or bug is absorbed as a known cost of the stack rather than a reason to switch.
- Carrying the TTS runtime libraries as dev deps means the local dev environment is heavier than the API's, but it buys **local type-checking of the full service code** without a GPU or a deployed image.
- Deviating from the usual Poetry default means this project's onboarding differs from sibling projects; the deviation is deliberate and recorded here.

## Alternatives considered and not chosen

- **Poetry (+ flake8/black + mypy)** — not chosen: the Astral stack is faster and consolidates dependency, lint, format, and type tooling behind fewer vendors and config files.
- **Skipping local type-checking of the TTS runtime code** (suppressing unresolved-import errors instead of installing the libs) — not chosen: it would leave the service's own code unchecked; installing the runtime libs as dev deps keeps all code type-checked.
