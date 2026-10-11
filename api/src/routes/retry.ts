import { claimRetry, database, getItem, ITEM_STATUS, writeStatus } from "@nagara/common";
import { restartItem } from "../items/restart.ts";
import { detail } from "../respond.ts";
import { toItemResponse } from "../response.ts";

export const retry = async (env: Cloudflare.Env, id: string) => {
  const db = database(env.DB);
  const row = await getItem(db, id);

  if (row == null) {
    return detail("item not found", 404);
  }

  const claimed = await claimRetry(db, row, env.RETRY_MAX);

  // Read again after a lost claim so the answer names the status the winner wrote.
  if (claimed == null) {
    const current = await getItem(db, id);

    if (current == null) {
      return detail("item not found", 404);
    }

    return current.status === ITEM_STATUS.failed
      ? detail(`retry limit reached (${env.RETRY_MAX})`, 409)
      : detail(`item is ${current.status}, not failed`, 409);
  }

  // The claim already counted this retry, so a restart that fails leaves the item failed with
  // the count spent rather than queued with nothing running it. The claim also required the item
  // to be failed, so an instance that still reports itself live is restarted all the same.
  try {
    await restartItem(env.ITEM_WORKFLOW, claimed, { leaveLive: false });
  } catch (error) {
    const failed = await writeStatus(db, id, {
      status: ITEM_STATUS.failed,
      currentStep: claimed.current_step,
      error: String(error),
    });

    return Response.json(toItemResponse(failed ?? claimed), { status: 202 });
  }

  return Response.json(toItemResponse(claimed), { status: 202 });
};
