import { claimRequeue, type Database, ITEM_STATUS, type ItemRow } from "@nagara/common";
import { restartItem } from "./restart.ts";

// The claim is one conditional write so two polls landing together restart the instance once;
// it leaves retry_count alone because a re-queue recovers an item that never failed. The check
// before it only spares a write on the polls of an item that is not stale. An instance that is
// still running or waiting is left alone: a slow item is not a stranded one.
export const requeueIfStale = async (env: Cloudflare.Env, db: Database, row: ItemRow) => {
  const staleBefore = Date.now() - env.REQUEUE_AFTER_MS;

  if (row.status !== ITEM_STATUS.queued || Date.parse(row.queued_at) >= staleBefore) {
    return;
  }

  if ((await claimRequeue(db, row.id, new Date(staleBefore).toISOString())) == null) {
    return;
  }

  // The claim already moved queued_at, so a failure here waits for the next stale poll.
  try {
    await restartItem(env.ITEM_WORKFLOW, row, { leaveLive: true });
  } catch (error) {
    console.error(`re-queue of ${row.id} could not restart its Workflow: ${String(error)}`);
  }
};
