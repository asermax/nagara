import { database, getItem } from "@nagara/common";
import { requeueIfStale } from "../items/requeue.ts";
import { detail } from "../respond.ts";
import { toItemResponse } from "../response.ts";

export const poll = async (env: Cloudflare.Env, id: string) => {
  const db = database(env.DB);
  const row = await getItem(db, id);

  if (row == null) {
    return detail("item not found", 404);
  }

  await requeueIfStale(env, db, row);

  return Response.json(toItemResponse(row));
};
