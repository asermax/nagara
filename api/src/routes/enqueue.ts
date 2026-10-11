import { ITEM_STATUS, readItem, writeStatus } from "@nagara/common";
import * as v from "valibot";
import { insertQueued } from "../items/create.ts";
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

  const itemId = await insertQueued(env.DB, {
    url: parsed.output.url,
    voice: pickVoice(parsed.output.voice),
  });

  try {
    await env.ITEM_WORKFLOW.create({ params: { itemId } });
  } catch (error) {
    await writeStatus(env.DB, itemId, {
      status: ITEM_STATUS.failed,
      currentStep: null,
      error: String(error),
    });
  }

  const row = await readItem(env.DB, itemId);

  if (row == null) {
    throw new Error(`item ${itemId} vanished right after its insert`);
  }

  return Response.json(toItemResponse(row), { status: 202 });
};
