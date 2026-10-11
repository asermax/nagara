import { hasValidKey } from "./guard.ts";
import { detail } from "./respond.ts";
import { audio } from "./routes/audio.ts";
import { enqueue } from "./routes/enqueue.ts";
import { images } from "./routes/images.ts";
import { poll } from "./routes/poll.ts";
import { retry } from "./routes/retry.ts";

const ITEM_ROUTE = /^\/items\/([^/]+)$/;
const RETRY_ROUTE = /^\/items\/([^/]+)\/retry$/;
const AUDIO_ROUTE = /^\/items\/([^/]+)\/audio$/;
const IMAGE_ROUTE = /^\/items\/([^/]+)\/images\/([^/]+)$/;

const route = async (request: Request, env: Cloudflare.Env, path: string) => {
  if (request.method === "POST" && path === "/items") {
    return await enqueue(request, env);
  }

  const itemMatch = path.match(ITEM_ROUTE);

  if (request.method === "GET" && itemMatch != null) {
    return await poll(env, itemMatch[1]);
  }

  const retryMatch = path.match(RETRY_ROUTE);

  if (request.method === "POST" && retryMatch != null) {
    return await retry(env, retryMatch[1]);
  }

  const audioMatch = path.match(AUDIO_ROUTE);

  if (request.method === "GET" && audioMatch != null) {
    return await audio(env, audioMatch[1]);
  }

  const imageMatch = path.match(IMAGE_ROUTE);

  if (request.method === "GET" && imageMatch != null) {
    return await images(env, imageMatch[1], imageMatch[2]);
  }

  return detail("not found", 404);
};

export default {
  async fetch(request: Request, env: Cloudflare.Env): Promise<Response> {
    const path = new URL(request.url).pathname;

    if (path === "/health") {
      return new Response("ok");
    }

    if (!hasValidKey(request, env)) {
      return detail("invalid or missing X-API-Key", 401);
    }

    return await route(request, env, path);
  },
} satisfies ExportedHandler<Cloudflare.Env>;
