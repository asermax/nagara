import { createItem, database, ITEM_STATUS, writeStatus } from "@nagara/common";
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
  const item = await createItem(db, {
    url: parsed.output.url,
    voice: pickVoice(parsed.output.voice),
  });

  try {
    await env.ITEM_WORKFLOW.create({ id: item.id, params: { itemId: item.id } });
  } catch (error) {
    const failed = await writeStatus(db, item.id, {
      status: ITEM_STATUS.failed,
      currentStep: null,
      error: String(error),
    });

    return Response.json(toItemResponse(failed ?? item), { status: 202 });
  }

  return Response.json(toItemResponse(item), { status: 202 });
};
