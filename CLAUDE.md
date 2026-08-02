# Nagara

**Nagara (ながら)**: from *ながら聞き*, consuming content *while doing something else*. A private,
API-first **audio read-later queue**: `enqueue(url, voice?) → generate eagerly → private item with
a listen link`. The TTS pipeline is proven; the open question is demand: see
[`docs/quest-log/validate-demand.md`](docs/quest-log/validate-demand.md).

## Layout and commands

| Tree | What it is |
|---|---|
| `api/` | The queue API: enqueue, poll, audio delivery, single-key auth |
| `tts/` | The GPU text-to-speech service: a separate Modal deployable the API invokes remotely |
| `web/` | The web surfaces: not yet built on `main`. The concluded read-along player spike is preserved on the `idea/read-along-player` branch with its tree relocated to `web/`, so checking that branch out is how you see what the spike settled; it is reference material, not a starting point |
| `docs/` | An Obsidian vault. **Read [`docs/README.md`](docs/README.md) before touching anything under it**, not only before adding a note, but before editing, renaming, or moving one. `technical-design/` is how the code works, `product-design/` is what nagara is, and a note explains how a part works, mechanism first, with reasoning in Obsidian callouts; it is not a decision record. `docs/quest-log/` is the quest log (one list of adventures and quests, told apart by a tag); see "The vault" below. |

```
api/   uv sync · uv run alembic upgrade head (once) · uv run uvicorn app.main:app --reload
       uv run pytest · uv run ruff check · uv run ty check
tts/   uv run modal serve app.py (dev) · uv run modal deploy app.py (prod)
       uv run pytest · uv run ruff check · uv run ty check
web/   pnpm dev · pnpm test · pnpm build · pnpm biome check      (not yet built)
```

Both `api/` and `tts/` are pinned to **Python 3.12** (Kokoro / `modal`-client constraints; the system
Python is newer). `tts/` carries the Modal image's runtime deps (kokoro/torch-cpu/numpy/soundfile) as
**dev** dependencies, not runtime ones, so `ty` can type-check all of `app.py` locally: do not "clean
up" those dependencies out of the dev group.

CI runs test/lint/types as three parallel jobs per subproject, each path-filtered to its own directory,
on pushes to `main`; `tts` adds a deploy job gated on all three checks. `api/` auto-deploys on push to
`main` via Railway's connected source: two dashboard-only Railway settings are load-bearing and not in
`railway.toml`; read [`docs/technical-design/deployment-and-ci.md`](docs/technical-design/deployment-and-ci.md)
before touching deploy configuration.

## Invariants that must not drift

These are decisions, not preferences. Each has a note in `docs/technical-design/invariants.md`
explaining what it buys; if the two disagree, that note is the explanation and this is the summary:
fix both.

1. **One extraction is the source of truth.** The spoken form never reaches a client and the display
   form is never synthesized: both are derived from one markdown segmentation.
2. **`display[i]`, `spoken[i]`, and `timeline[i]` are the same unit by construction, never by matching
   text.** A unit dropped for any reason is dropped from *both* lists.
3. **Timing windows are contiguous and the last `end` equals the audio duration.** The inter-paragraph
   pause is folded into the preceding window.
4. **Every route that touches an item requires the key**: enqueue, poll, and audio alike. `/health` is
   the only unauthenticated route.
5. **The API never imports the TTS code.** `tts/` is an image definition uploaded to Modal; the API
   spawns and resolves it remotely: no broker, no worker, no background sweeper.
6. **Which backend is a question about configuration, never an environment name.** No `if production`,
   no `if testing` in runtime code.
7. **A schema change is a migration.** Alembic owns the dev/prod schema.
8. **The two deployables ship independently, and neither pipeline reaches into the other's tree.**
9. **Read-along highlight sync is `requestAnimationFrame`, never `timeupdate`.** (Applies to `web/`,
   which does not exist yet.)

## Code style

Follows the global style guide, plus:

- **Payloads crossing a service boundary are modeled with pydantic** (the API's schemas and the TTS
  service's return shape alike), so they validate and type-check end to end.
- `api/app/` is `models` / `schemas` / `service` / `endpoints`: a new capability picks the matching
  package rather than growing a new top-level module.
- Comments explain **why**, never what; do not add narration alongside a comment that is already there
  for a non-obvious reason.
- A new or changed note is created from `docs/_templates/`; rationale goes in a `> [!note]` callout
  beside the mechanism it justifies, never as the note's spine. No hard wrapping: one line per
  paragraph.

## The vault

- **Vault**: `docs/`, an Obsidian vault. Read its `README.md` before adding, editing, renaming or
  moving anything under it: it is the authority on what each folder holds, how files are named, what
  frontmatter they carry, and how the indexes are generated.
- **Notes**: `technical-design/`, how the code works; `product-design/`, what nagara is.
- **Quest log**: `docs/quest-log/`, one list holding both adventures and quests, told apart by a tag.
- **Code**: `api/`, `tts/` (and `web/`, once it exists).
- **Run**: see "Layout and commands" above. · **Checks**: `uv run pytest` · `uv run ruff check` ·
  `uv run ty check`, in whichever of `api/`/`tts/` a change touches.
- **Seeing it work**: two failure modes pass every check and still don't work. **Extraction can succeed
  on the wrong thing**: a URL serving a 200-status error page extracts cleanly, generates audio, and
  reaches `ready`; the status is never `failed`, so a green pipeline is not evidence the item is the
  article (see `docs/quest-log/trustworthy-extraction.md`). **And you have to listen to it**: a
  strip regression is invisible in a diff and inaudible in a test summary, and unmistakable in one
  second of audio; a leaked `**` is only ever caught by playing the file.
- **Branch**: one per adventure (`adventure/<slug>`); throwaway spikes live in one worktree, on a
  branch that is never merged, cut by the venture and inherited by the raid that follows it, which
  is what strikes it. nagara reversed its original graduate-in-place convention — see
  `docs/quest-log/README.md`'s "How we work".

### When adding something

- **A new route** → an endpoint module + a pydantic schema + a section in
  `docs/technical-design/item-contract.md`.
- **A new extraction rule** → a function in `extract.py`, a case in `test_extract.py`, **and a
  fixture** (an extraction rule with no fixture is a rule nobody can re-check), plus a section or
  callout in `docs/technical-design/article-extraction.md`.
- **A change to the item JSON** → `docs/technical-design/item-contract.md` **and a migration**, because
  the display list is persisted across the async gap.
- **A new cross-environment capability** → an interface and a factory that reads configuration, never a
  branch (invariant 6), plus a paragraph in `docs/technical-design/persistence-and-storage.md`.
- **Anything that changes what a listener hears or sees** → a note or section in `docs/product-design/`.
- **A new hard-to-reverse decision** → an entry in "Invariants that must not drift" above and in
  `docs/technical-design/invariants.md`; anything smaller is a `> [!note]` callout beside the mechanism
  it justifies.
- **A change to how we work** → a line in `docs/quest-log/README.md`.
