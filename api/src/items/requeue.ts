import { ITEM_STATUS, type ItemRow } from "@nagara/common";
import { restartItem } from "./restart.ts";

// The claim is one conditional write so two polls landing together restart the instance once;
// it leaves retry_count alone because a re-queue recovers an item that never failed. The check
// before it only spares a write on the polls of an item that is not stale.
export const requeueIfStale = async (env: Cloudflare.Env, row: ItemRow) => {
  const now = Date.now();
  const staleBefore = now - env.REQUEUE_AFTER_MS;

  if (row.status !== ITEM_STATUS.queued || Date.parse(row.queued_at) >= staleBefore) {
    return;
  }

  const nowIso = new Date(now).toISOString();

  const claim = await env.DB.prepare(
    "UPDATE items SET queued_at = ?, updated_at = ? WHERE id = ? AND status = ? AND queued_at < ?",
  )
    .bind(nowIso, nowIso, row.id, ITEM_STATUS.queued, new Date(staleBefore).toISOString())
    .run();

  if (claim.meta.changes === 0) {
    return;
  }

  await restartItem(env.ITEM_WORKFLOW, row);
};
