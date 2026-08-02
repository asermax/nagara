---
title: "The typed unit contract"
tags:
  - quest
summary: "A display unit becomes a typed object carrying its markdown, its type and its spoken form, the wire list renames to units[], and 108 live items migrate in place."
status: open
kind: build
adventure: richer-extraction
blocked_by: []
priority: 1-now
created: "2026-08-02"
---

# The typed unit contract

## What

Release 1 of [[richer-extraction]], and it ships alone. Every unit comes out a `paragraph`, nothing a listener hears changes, and the one irreversible step in the whole adventure is isolated where it can be verified by itself.

Enqueue an article and poll it: the response carries `units[]` where it carried `paragraphs[]`, each element `{index, type, display, start, end}` with no `spoken`. The 108 items already in production keep working.

Everything else in the adventure is blocked on this, because the type discriminator is what the fence guard flips, what the image injection sets, and what a degradation record reuses.

## Design

### Two shapes, because `spoken` is internal

The persisted `Unit` is a discriminated union sharing `type`, `display` and `spoken`, with `ImageUnit` adding `image`:

| Variant | Fields |
|---|---|
| `ParagraphUnit` | `type="paragraph"`, `display`, `spoken` |
| `CodeUnit` | `type="code"`, `display`, `spoken` |
| `ImageUnit` | `type="image"`, `display`, `spoken`, `image` |

The wire element is `{index, type, display, start, end}`, plus `image` on an image unit. `spoken` is required on every persisted variant and projected out at the response boundary. That projection is the mechanism keeping invariant 1's oldest clause true.

A single model with an optional `image` field was rejected: the union puts the image reference where it is non-optional and absent everywhere else.

### Vocabulary

| Today | Becomes |
|---|---|
| `Paragraph` | `Unit`, the union above |
| `paragraphs[]` on the wire | `units[]` |
| `.text` | `.display` |
| `display` and `paragraphs` columns | one `units` column |
| `paragraphs_from_markdown` | `units_from_markdown` |

Three types and no more. Tables, blockquotes, list items and headings all fold to `paragraph`: the display markdown already carries the structure a renderer needs, and no pipeline branch treats them differently. `code` and `image` earn a type because the pipeline does branch on them.

Spoken derivation keeps sniffing the markdown shape, so a paragraph unit whose display starts with `|` still routes through `_table_to_spoken`. The type's job is to say which units enrich, not to re-encode what the markdown says.

`UNIT_TYPES` is a constant map with the pydantic discriminator a `Literal` derived from it, per the project's no-enum rule. `ItemStatus` is an existing `StrEnum` and stays one.

### Where the type is decided

`_split_units` tags provisionally as it already branches: fence to `code`, everything else to `paragraph`. Two later quests refine it, and the shape has to allow both. [[fence-segmentation-repair]] flips `code` to `paragraph` on a re-classified block, at extraction time. [[article-image-units]] injects `image` units during enrichment. The discriminator is settled before a unit reaches the persisted list.

### `ImageUnit.image` is the content hash

Not a URL. The route path is reconstructed at read time from the item id and the hash, because a presigned URL written into the row would be dead inside `s3_url_ttl` and the unit list is persisted. No origin URL is ever retained.

Nothing else earns a field. No `language` on code: absent from the corpus, inferred by the describer, and it rides in the display markdown untouched if a fence ever carries one. No separate `alt`: it rides in the display markdown. No `caption`: it is consumed into `spoken` verbatim.

The image unit's display-markdown construction, whether a bare `![alt](path)` or a figure, is a build detail for [[article-image-units]]. This quest fixes only that the hash is the reference.

### The migration

One revision, `down_revision = 43f4ed0fcb35`, doing all of it so no intermediate state exists:

1. `DELETE` rows with status `generating` and no `paragraphs`. Five rows, permanently stranded.
2. `UPDATE items SET status = lower(status)`, normalizing the `READY`/`ready` casing drift that is live in both databases.

> [!warning] Step 2 is a data fix **plus** a model change, and found during the build
> `Enum(ItemStatus, native_enum=False)` stores the enum **by name**, so the column holds `READY` rather than `ready`. Verified: the default declaration yields `['GENERATING', 'READY', 'FAILED']`. Lowercasing live rows without touching the model makes every ORM read raise `LookupError: 'ready' is not among the defined enum values`, and every new write re-uppercases, so the drift returns.
>
> The migration therefore ships with `values_callable=lambda e: [m.value for m in e]` on the column, which stores and reads by value. This is also **where the production drift came from**: rows the ORM wrote are uppercase and rows written another way are not.
>
> A related divergence, worth knowing before the dry-run: the initial migration declares `status` as a plain `sa.String()` with **no CHECK constraint**, while `init_db()` builds it from the model *with* one. So `lower(status)` is safe against production and the two schemas were never identical. That is invariant 7's unexercised-migration gap, concretely.
3. Add `units` (JSON, nullable).
4. Backfill per row: `units[i] = {index, type: "paragraph", display: display[i] or paragraphs[i].text, spoken: paragraphs[i].text, start, end}`.
5. Drop `display` and `paragraphs`.

`index`, `start` and `end` come across verbatim, so invariant 3 holds and the last `end` still equals the audio duration. Invariant 2 holds by construction, because all three fields are built from one source row and never matched by text.

Every old unit becomes `paragraph`, including the 99 that hold a fence. Inferring `code` from the fence was rejected: the transform stays uniform, and because `display` is preserved inside the unit, re-tagging later is a pure function of the stored data.

`downgrade()` rebuilds both columns from `units` and cannot restore the five deleted rows.

Re-extracting to recover richer display was never available: a fresh extraction segments differently, so aligning it against an old timeline is exactly the text matching invariant 2 forbids.

### What production actually holds

Queried read-only at revision `43f4ed0fcb35`. The dev database disagrees with this and is misleading.

| Cohort | Rows | Disposition |
|---|---:|---|
| ready, `display` + `paragraphs`, length-aligned in every row | 96 | transformed losslessly |
| ready, `paragraphs` but no `display` | 3 | transformed, `display = spoken` |
| `GENERATING`, `display` but no `paragraphs` | 5 | deleted |
| failed | 4 | untouched |

> [!warning] 24 of the 96 ready items have audio that reads code aloud, and this quest does not fix it
> 99 units, 2.8% of all 3,553 in production, carry raw code as their spoken text: backticks and `@startuml`, read out by Kokoro, because `_to_spoken`'s `"Code sample."` rule is newer than every item live. Transform all 96 identically and accept it. The display markdown is correct so a reader is unaffected; a listener on those 24 keeps bad audio until someone re-enqueues by hand.

### Invariants

Both updates land in `invariants.md` **and** the `CLAUDE.md` summary in the same pass, because `CLAUDE.md` says fix both together or they drift.

Invariant 1 keeps its first clause and changes its second. New text: *One extraction is the source of truth. The spoken form never reaches a client and the display form is never synthesized: both come from one markdown segmentation and ride on the same typed unit.* The clause about the spoken form is load-bearing, because it is the reason for the response filter. What changes is the rest: code and image spoken forms are generated and anchored to the unit rather than stripped from markdown.

Invariant 2 tightens. There is one unit list where there were two parallel lists, so a dropped unit leaves the one list and its timeline window goes with it. A length mismatch at finalize still fails the item.

### How it is verified

`store_result`'s existing guard is unchanged: `len(units) == len(timeline)` or the item fails. A generated spoken form joins exactly like a derived one, same index, same shape.

Seam 1, the HTTP surface, covers the wire projection: `units[]` present, `spoken` absent, `type` on every element. Seam 2, `units_from_markdown`, covers provisional typing.

**The migration is verified by a manual dry-run against a copy of the production database before merging.** Not a test. A permanent migration test was offered and declined; the consequence is that `tests/conftest.py` builds its schema with `init_db()`, so `alembic upgrade head` stays unexercised by CI for this migration and every future one.

> [!warning] Run the migration when nothing is in flight
> `preDeployCommand` runs while the old release is still serving traffic, so an item genuinely mid-synthesis at that moment matches the stranded-row `DELETE` and is destroyed.

### What has never been tried

No corpus unit has been round-tripped through this contract. The decisions rest on sibling quests' measurements and the existing extraction code. This build must verify a real article's units serialize, persist, project with `spoken` filtered, and re-join timing end to end.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[item-contract]] · [[invariants]] · [[article-extraction]]
