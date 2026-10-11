import { ITEM_STATUS } from "@nagara/common";

// A read-then-write would let two concurrent retries both pass the guard, so the write itself
// decides: only the first finds the item still failed and under the cap.
export const claimRetry = async (db: D1Database, id: string, retryMax: number) => {
  const now = new Date().toISOString();

  const claim = await db
    .prepare(
      "UPDATE items SET status = ?, error = NULL, queued_at = ?, updated_at = ?, retry_count = retry_count + 1 WHERE id = ? AND status = ? AND retry_count < ?",
    )
    .bind(ITEM_STATUS.queued, now, now, id, ITEM_STATUS.failed, retryMax)
    .run();

  return claim.meta.changes > 0;
};
