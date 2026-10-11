import { audioKey, ITEM_STATUS, readItem } from "@nagara/common";
import { detail } from "../respond.ts";
import { signedRedirect } from "./signed-redirect.ts";

export const audio = async (env: Cloudflare.Env, id: string) => {
  const row = await readItem(env.DB, id);

  if (row == null || row.status !== ITEM_STATUS.ready || row.audio_format == null) {
    return detail("audio not available", 404);
  }

  return await signedRedirect(env, audioKey(id));
};
