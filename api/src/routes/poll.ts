import { ITEM_STATUS, readItem } from "@nagara/common";
import { requeue } from "../items/requeue.ts";
import { detail } from "../respond.ts";
import { toItemResponse } from "../response.ts";

export const poll = async (env: Cloudflare.Env, id: string) => {
  const row = await readItem(env.DB, id);

  if (row == null) {
    return detail("item not found", 404);
  }

  if (
    row.status === ITEM_STATUS.queued &&
    Date.now() - Date.parse(row.queued_at) > env.REQUEUE_AFTER_MS
  ) {
    await requeue(env, row);
  }

  return Response.json(toItemResponse(row));
};
