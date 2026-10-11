# drizzle on D1

`common/` reaches D1 through drizzle-orm and generates its migrations with drizzle-kit. The pinned versions are drizzle-orm 0.45.4 and drizzle-kit 0.31.11, the npm `latest` tags. drizzle-kit 0.31.11 writes each migration as a top-level `NNNN_name.sql`, with `--> statement-breakpoint` comments between statements, plus a `meta/` folder of snapshots; `wrangler d1 migrations apply --local` applied that output without errors, CHECKs and `json_valid` included.

- Do not move to the drizzle-kit 1.0 release candidate while wrangler applies the migrations. The release candidate writes each migration into its own timestamped subfolder, and both `wrangler d1 migrations apply` and `readD1Migrations` from `@cloudflare/vitest-pool-workers` read only top-level `.sql` files in the migrations folder, so neither finds a migration.
- `text({ enum: [...] })` types the column but emits no CHECK constraint. Add an explicit `check()` in the table's extra config for every enum column that the database must enforce.
- drizzle-kit 0.x writes the columns inside a `check()` qualified with their table (`"items"."status"`). SQLite and D1 accept it; expect that form when reviewing a generated migration.
- A JSON column is `text({ mode: "json" }).$type<T>()`: drizzle encodes on write and decodes on read, so no hand-written codec is needed. Add the `json_valid` CHECK with `check()`.
- `integer({ mode: "boolean" })` reads back `true`/`false` instead of `1`/`0`.
- `db.batch([...])` is D1's transaction: D1 runs the batch atomically. `db.transaction(...)` does not work against a D1 binding, because D1 rejects `BEGIN` from a Worker. A write that depends on a read has to be one conditional statement; with `.returning()`, an empty result means the statement matched no row.
- A query function returns the query unawaited so the caller can either await it or put it in a batch.
