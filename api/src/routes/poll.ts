import { readItem } from "@nagara/common";
import { requeueIfStale } from "../items/requeue.ts";
import { detail } from "../respond.ts";
import { toItemResponse } from "../response.ts";

export const poll = async (env: Cloudflare.Env, id: string) => {
  const row = await readItem(env.DB, id);

  if (row == null) {
    return detail("item not found", 404);
  }

  await requeueIfStale(env, row);

  return Response.json(toItemResponse(row));
};
