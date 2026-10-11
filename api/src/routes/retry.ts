import { claimRetry, database, getItem, ITEM_STATUS, writeStatus } from "@nagara/common";
import { restartItem } from "../items/restart.ts";
import { detail } from "../respond.ts";
import { toItemResponse } from "../response.ts";

export const retry = async (env: Cloudflare.Env, id: string) => {
  const db = database(env.DB);
  const read = await getItem(db, id);

  if (read == null) {
    return detail("item not found", 404);
  }

  const claimed = await claimRetry(db, read, env.RETRY_MAX);

  // Read again after the claim so a retry that lost the race reports the status the winner wrote,
  // and a claimed item answers with the status and count the claim wrote.
  const row = (await getItem(db, id)) ?? read;

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
    await writeStatus(db, id, {
      status: ITEM_STATUS.failed,
      currentStep: row.current_step,
      error: String(error),
    });

    return Response.json(toItemResponse((await getItem(db, id)) ?? row), { status: 202 });
  }

  return Response.json(toItemResponse(row), { status: 202 });
};
