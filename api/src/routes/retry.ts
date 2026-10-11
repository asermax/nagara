import { ITEM_STATUS, readItem, writeStatus } from "@nagara/common";
import { restartItem } from "../items/restart.ts";
import { claimRetry } from "../items/retry-claim.ts";
import { detail } from "../respond.ts";
import { toItemResponse } from "../response.ts";

export const retry = async (env: Cloudflare.Env, id: string) => {
  const claimed = await claimRetry(env.DB, id, env.RETRY_MAX);

  // Read after the claim so a retry that lost the race reports the status the winner wrote.
  const row = await readItem(env.DB, id);

  if (row == null) {
    return detail("item not found", 404);
  }

  if (!claimed) {
    return row.status === ITEM_STATUS.failed
      ? detail(`retry limit reached (${env.RETRY_MAX})`, 409)
      : detail(`item is ${row.status}, not failed`, 409);
  }

  // The claim already counted this retry, so a restart that fails leaves the item failed with
  // the count spent rather than queued with nothing running it. The claim also required the item
  // to be failed, so an instance that still reports itself live is restarted all the same.
  try {
    await restartItem(env.ITEM_WORKFLOW, row, { leaveLive: false });
  } catch (error) {
    await writeStatus(env.DB, id, {
      status: ITEM_STATUS.failed,
      currentStep: row.current_step,
      error: String(error),
    });

    return Response.json(toItemResponse((await readItem(env.DB, id)) ?? row), { status: 202 });
  }

  return Response.json(toItemResponse(row), { status: 202 });
};
