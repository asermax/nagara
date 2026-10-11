import { imageKey, readItem } from "@nagara/common";
import { detail } from "../respond.ts";
import { signedRedirect } from "./signed-redirect.ts";

// The hash is signed without checking the object exists: R2 answers an unknown hash with its own
// 404, which spares a HEAD on a route every render hits many times.
export const images = async (env: Cloudflare.Env, id: string, hash: string) => {
  if ((await readItem(env.DB, id)) == null) {
    return detail("item not found", 404);
  }

  return await signedRedirect(env, imageKey(hash));
};
