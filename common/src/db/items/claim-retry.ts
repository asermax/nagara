import { and, eq, lt } from "drizzle-orm";
import { ITEM_STATUS, type ItemRow } from "../../item.ts";
import type { Database } from "../database.ts";
import { items } from "../schema.ts";

// A read-then-write would let two concurrent retries both pass the guard, so the write itself
// decides: only the first finds the item still failed, still at the count it read and under the
// cap. The claimed row comes back, or null when this call lost.
export const claimRetry = async (db: Database, { id, retry_count }: ItemRow, retryMax: number) =>
  (await db
    .update(items)
    .set({
      status: ITEM_STATUS.queued,
      error: null,
      queued_at: new Date().toISOString(),
      retry_count: retry_count + 1,
    })
    .where(
      and(
        eq(items.id, id),
        eq(items.status, ITEM_STATUS.failed),
        eq(items.retry_count, retry_count),
        lt(items.retry_count, retryMax),
      ),
    )
    .returning()
    .get()) ?? null;
