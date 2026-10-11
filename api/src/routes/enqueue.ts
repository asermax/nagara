import { createItem, database, getItem, ITEM_STATUS, writeStatus } from "@nagara/common";
import * as v from "valibot";
import { detail } from "../respond.ts";
import { toItemResponse } from "../response.ts";
import { pickVoice } from "../voices.ts";

const enqueueBody = v.object({
  url: v.string(),
  voice: v.optional(v.string()),
});

const parseBody = async (request: Request) => {
  try {
    return v.safeParse(enqueueBody, await request.json());
  } catch {
    return null;
  }
};

export const enqueue = async (request: Request, env: Cloudflare.Env) => {
  const parsed = await parseBody(request);

  if (parsed == null || !parsed.success) {
    return detail("the body needs a url string and an optional voice string", 400);
  }

  const db = database(env.DB);
  const { id: itemId, query } = createItem(db, {
    url: parsed.output.url,
    voice: pickVoice(parsed.output.voice),
  });

  await query;

  try {
    await env.ITEM_WORKFLOW.create({ id: itemId, params: { itemId } });
  } catch (error) {
    await writeStatus(db, itemId, {
      status: ITEM_STATUS.failed,
      currentStep: null,
      error: String(error),
    });
  }

  const row = await getItem(db, itemId);

  if (row == null) {
    throw new Error(`item ${itemId} vanished right after its insert`);
  }

  return Response.json(toItemResponse(row), { status: 202 });
};
