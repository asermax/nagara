import { and, eq, lt } from "drizzle-orm";
import { ITEM_STATUS, type ItemRow } from "../../item.ts";
import type { Database } from "../database.ts";
import { items } from "../schema.ts";

// A read-then-write would let two concurrent retries both pass the guard, so the write itself
// decides: only the first finds the item still failed, still at the count it read and under the
// cap.
export const claimRetry = async (db: Database, { id, retry_count }: ItemRow, retryMax: number) => {
  const now = new Date().toISOString();

  const claimed = await db
    .update(items)
    .set({
      status: ITEM_STATUS.queued,
      error: null,
      queued_at: now,
      updated_at: now,
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
    .returning({ id: items.id });

  return claimed.length > 0;
};
