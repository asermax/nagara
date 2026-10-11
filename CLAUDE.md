# Nagara

**Nagara (ながら)**: from *ながら聞き*, consuming content *while doing something else*. A private,
API-first **audio read-later queue**: `enqueue(url, voice?) → generate eagerly → private item with
a listen link`. The TTS pipeline is proven; the open question is demand: see
[`docs/product-design/what-nagara-is.md`](docs/product-design/what-nagara-is.md).

## Layout and commands

| Tree | What it is |
|---|---|
| `api/` | The API Worker: the only routes clients reach (enqueue, poll, retry, audio, images, health), behind a single API key; it writes the item row at enqueue and creates and restarts the item Workflow |
| `tts/` | The GPU text-to-speech service: a separate Modal deployable the item Workflow calls through two web endpoints |
| `pipeline/` | The pipeline Worker on Cloudflare, with no public routes: the item Workflow that does all the work for one item, a DomainQueue Durable Object per domain, the recipe runtime, the Flue author and revision agents |
| `common/` | The package both Workers build from: the shared types, the R2 key layout, presigning, the drizzle schema of D1 with a query function for every read and write, the SQL migrations drizzle-kit generates from that schema, and the cassette replay library. Only the migrations are deployed |
| `web/` | The web surfaces: not yet built on `main`. The concluded read-along player spike is preserved on the `idea/read-along-player` branch with its tree relocated to `web/`, so checking that branch out is how you see what the spike settled; it is reference material, not a starting point |
| `docs/` | The documentation. **Read [`docs/README.md`](docs/README.md) before touching anything under it**, not only before adding a note, but before editing, renaming, or moving one. `technical-design/` is how the code works, `product-design/` is what nagara is, and a note explains how a part works, mechanism first, with reasoning in callouts; it is not a decision record. Work in flight lives in Linear, never in `docs/`; see "Work tracking" below. |

```
tts/       uv run modal serve app.py (dev) · uv run modal deploy app.py (prod)
           uv run pytest · uv run ruff check · uv run ty check
pipeline/  pnpm install · pnpm dev (vite dev, 5173) · pnpm dev:proxy · pnpm run deploy (prod, via wrangler)
           pnpm test · pnpm lint · pnpm types
api/       pnpm dev (wrangler dev, 8788) · pnpm run deploy (prod, via wrangler)
           pnpm test · pnpm lint · pnpm types
common/    pnpm db:generate (migration from the schema) · pnpm db:check (schema and migrations agree) · pnpm migrate:local (D1 in the shared state folder)
           pnpm test · pnpm lint · pnpm types
web/       pnpm dev · pnpm test · pnpm build · pnpm biome check      (not yet built)
```

Locally both Workers share one state folder, with D1 and R2 on disk, and Modal uploads audio through a
quick tunnel and a local proxy: read
[`docs/technical-design/local-development.md`](docs/technical-design/local-development.md) before
running them together.

`tts/` is pinned to **Python 3.12** (Kokoro / `modal`-client constraints; the system Python is
newer). `tts/` carries the Modal image's runtime deps (kokoro/torch-cpu/numpy/soundfile) as
**dev** dependencies, not runtime ones, so `ty` can type-check all of `app.py` locally: do not "clean
up" those dependencies out of the dev group.

CI runs test/lint/types as three parallel jobs per subproject, each path-filtered to its own directory,
on pushes to `main`; a change to `common/` also runs the type checks of `api/` and `pipeline/`. One
Cloudflare workflow deploys with wrangler in a fixed order: it applies `common/`'s migrations to D1, then
deploys the pipeline Worker from the built `dist/nagara/wrangler.json`, then the API Worker; a job runs
only when no job before it failed, so a failed check in `common/` stops all three. `tts` adds a deploy job to Modal gated on its own three checks. Read
[`docs/technical-design/deployment-and-ci.md`](docs/technical-design/deployment-and-ci.md) before
touching deploy configuration.

## Invariants that must not drift

These are decisions, not preferences. Each has a note in `docs/technical-design/invariants.md`
explaining what it buys; if the two disagree, that note is the explanation and this is the summary:
fix both.

1. **One extraction is the source of truth.** The spoken form never reaches a client and the display
   form is never synthesized: both come from one markdown segmentation and ride on the same typed unit.
2. **Display, spoken, and timing ride on one typed unit, never matched by text.** A dropped unit leaves
   the one list and its window goes with it; a length mismatch at finalize fails the item.
3. **Timing windows are contiguous and the last `end` equals the audio duration.** The inter-paragraph
   pause is folded into the preceding window.
4. **Every route that touches an item requires the key**: enqueue, poll, and audio alike. `/health` is
   the only unauthenticated route.
5. **No Worker imports the TTS code.** `tts/` is an image definition uploaded to Modal; the item
   Workflow reaches it over HTTP through two web endpoints behind Modal's proxy auth: no broker, no
   background sweeper. Deferred work runs as the item Workflow's steps, each retried on its own; the
   retry route restarts a failed item from the step that failed, and the API queues an item again
   when it reads one that has been queued for more than 15 minutes.
6. **Which backend is a question about configuration, never an environment name.** No `if production`,
   no `if testing` in runtime code.
7. **A schema change is a migration.** The D1 schema is `common/src/db/schema.ts`; drizzle-kit
   generates the SQL migration from it, and the developer reviews and commits the migration. Migrations are
   applied before either Worker deploys; the Workers' tests build their schema from the same
   migrations.
8. **The three deployables ship separately, and no CI pipeline runs on another's tree except
   `common/`'s.** A change to `common/` runs both Workers' type checks; the Cloudflare side deploys
   `common/`'s migrations, then the pipeline Worker, then the API Worker.
9. **Read-along highlight sync is `requestAnimationFrame`, never `timeupdate`.** (Applies to `web/`,
   which does not exist yet.)
10. **A settled recipe always runs through the deterministic runtime.** The agent judges, the runtime
    extracts: an authored or revised script is handed back as source and run like any other recipe, so
    a fresh recipe and a years-old one extract through the same deterministic path.

## Code style

Follows the global style guide, plus:

- **Payloads crossing a service boundary are typed**: what the Workers share (the item row, the unit
  union, the item Workflow's params) is a TypeScript type in `common/`, and the TTS service's request
  and return shapes are pydantic models in `tts/`. The Workers' types are checked when the code builds,
  never at runtime: a value read back from D1 or received from Modal is trusted to match its type.
- Everything both Workers use lives in `common/`; code that only `pipeline/` modules share stays in
  `pipeline/`, in the module it belongs to, and the others import it from there. Each module inside
  `pipeline/` is as independent of the others as it can be.
- The database is the exception: every D1 read and write is a drizzle function in
  `common/src/db/`, even when only one Worker uses it. Each table has a folder of functions named by
  one pattern, `get<Model>`, `list<Models>`, `create<Model>`, `update<Model>` and `delete<Model>`,
  plus a conditional write named for what it does (`claimRetry`) when a plain update cannot express
  it. A write that spans tables and has to commit atomically is a function of its own in
  `common/src/db/operations/`, named for what it records (`recordFetch`). Every function runs its
  query and returns the row it read or wrote. A Worker builds the client and passes it to these
  functions. No route or step writes SQL or builds a batch.
- **A test double never reaches the production bundle.** The tests wire a fake in through the vitest
  configuration, such as a module the config substitutes, never through a setting or a branch the
  deployed code carries. After a build, `dist/` contains none of the fake's code.
- Comments explain **why**, never what; do not add narration alongside a comment that is already there
  for a non-obvious reason.
- A new or changed note is created from `docs/_templates/note.md`; rationale goes in a `> [!NOTE]`
  callout beside the mechanism it justifies, never as the note's spine. No hard wrapping: one line per
  paragraph.

## Docs

- **Docs**: `docs/`. Read its `README.md` before adding, editing, renaming or moving anything under it.
- **Folders**: `technical-design/`, how the code works; `product-design/`, what nagara is.
- **Run**: see "Layout and commands" above.
- **Checks**: `pnpm test` · `pnpm lint` · `pnpm types` in whichever of `api/`, `pipeline/` and
  `common/` a change touches (both Workers' as well when it touches `common/`); `uv run pytest` ·
  `uv run ruff check` · `uv run ty check` in `tts/`.
- **Seeing it work**: two failure modes pass every check and still don't work. **Extraction can succeed
  on the wrong thing**: a URL serving a 200-status error page extracts cleanly, generates audio, and
  reaches `ready`; the status is never `failed`, so a green pipeline is not evidence the item is the
  article. **And you have to listen to it**: a strip regression is invisible in a diff and inaudible in
  a test summary, and unmistakable in one second of audio; a leaked `**` is only ever caught by
  playing the file.

### When adding something

- **A new route** → a route in the API Worker + its request and response types + a section in
  `docs/technical-design/item-contract.md`.
- **A new rule for what a page yields** → the pipeline's runtime or the authoring prompts, plus a
  section or callout in `docs/technical-design/recipes.md`.
- **A new rule for how the recipe step's units become the item's** (the spoken form, the drop) → a function
  at the end of the item Workflow's recipe step in `pipeline/`, beside the spoken-form derivation, and a
  test case, plus a section or callout in
  `docs/technical-design/article-extraction.md`.
- **A change to the item JSON** → `docs/technical-design/item-contract.md`, **and a migration in
  `common/` when the persisted shape needs a backfill**: edit `common/src/db/schema.ts` and run
  `pnpm db:generate` in `common/`. Write the backfill because the item Workflow persists the display list across the async gap: a later step or request
  reads the in-flight item back, and that reader is not the step that wrote the row. **A new member of the unit union needs neither**: the item row's `units` is a JSON column, so the union
  is not schema and there is no DDL to write, and rows persisted before the new kind existed carry none
  of it and stay readable unchanged.
- **A schema change** → an edit to `common/src/db/schema.ts` and `pnpm db:generate` in `common/`,
  with the generated SQL reviewed and committed beside it (invariant 7), plus the query functions in
  `common/src/db/` that read and write the change.
- **A new cross-environment capability** → an interface and a factory that reads configuration, never a
  branch (invariant 6), plus a paragraph in `docs/technical-design/persistence-and-storage.md`.
- **Anything both Workers use** → `common/`, described in the note of the part that uses it,
  with a link to `docs/technical-design/common-package.md`.
- **Anything that changes what a listener hears or sees** → a note or section in `docs/product-design/`.
- **A new hard-to-reverse decision** → an entry in "Invariants that must not drift" above and in
  `docs/technical-design/invariants.md`; anything smaller is a `> [!NOTE]` callout beside the mechanism
  it justifies.

## Work tracking

- **Linear** holds the backlog: workspace `asermax`, team Asermax (key `ASE`), project **nagara**. A
  milestone is a feature; an issue is one task under it, or a loose task with no milestone. Labels are
  `Bug`, `Feature`, `Improvement` and `Spike` (throwaway code written to answer a question). Priority is
  High, Medium or Low. `Backlog` is the default status and `Todo` marks what is about to be worked on.
- **A feature is shaped and designed before it is built.** `mahou:shape` and `mahou:design` settle it
  with the user, the design lands as a note under `docs/`, and only then does a milestone get its
  implementation tasks. A spike precedes that when a question needs code to answer, and it is
  throwaway: it never merges.
- **A note never links to an issue.** An issue may cite a note by path. The issue closes and the link
  would rot; the note is maintained for as long as the part exists.
- **Branches** are `feat/<feature-name>`, one per feature.
