import type { ItemRow } from "@nagara/common";
import { restartItem } from "./restart.ts";

// The claim is one conditional write so two polls landing together restart the instance once;
// it leaves retry_count alone because a re-queue recovers an item that never failed.
export const requeue = async (env: Cloudflare.Env, row: ItemRow) => {
  const now = new Date();
  const staleBefore = new Date(now.getTime() - env.REQUEUE_AFTER_MS).toISOString();

  const claim = await env.DB.prepare(
    "UPDATE items SET queued_at = ?, updated_at = ? WHERE id = ? AND status = 'queued' AND queued_at < ?",
  )
    .bind(now.toISOString(), now.toISOString(), row.id, staleBefore)
    .run();

  if (claim.meta.changes === 0) {
    return;
  }

  await restartItem(env.ITEM_WORKFLOW, row);
};
