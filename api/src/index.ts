import { hasValidKey } from "./guard.ts";
import { detail } from "./respond.ts";
import { audio } from "./routes/audio.ts";
import { enqueue } from "./routes/enqueue.ts";
import { images } from "./routes/images.ts";
import { poll } from "./routes/poll.ts";
import { retry } from "./routes/retry.ts";

type Route = {
  method: string;
  path: RegExp;
  handle: (request: Request, env: Cloudflare.Env, params: string[]) => Promise<Response>;
};

const ROUTES: Route[] = [
  { method: "POST", path: /^\/items$/, handle: enqueue },
  { method: "GET", path: /^\/items\/([^/]+)$/, handle: (_, env, [id]) => poll(env, id) },
  { method: "POST", path: /^\/items\/([^/]+)\/retry$/, handle: (_, env, [id]) => retry(env, id) },
  { method: "GET", path: /^\/items\/([^/]+)\/audio$/, handle: (_, env, [id]) => audio(env, id) },
  {
    method: "GET",
    path: /^\/items\/([^/]+)\/images\/([^/]+)$/,
    handle: (_, env, [id, hash]) => images(env, id, hash),
  },
];

export default {
  async fetch(request: Request, env: Cloudflare.Env): Promise<Response> {
    const path = new URL(request.url).pathname;

    if (path === "/health") {
      return new Response("ok");
    }

    if (!hasValidKey(request, env)) {
      return detail("invalid or missing X-API-Key", 401);
    }

    for (const { method, path: pattern, handle } of ROUTES) {
      const match = request.method === method ? path.match(pattern) : null;

      if (match != null) {
        return await handle(request, env, match.slice(1));
      }
    }

    return detail("not found", 404);
  },
} satisfies ExportedHandler<Cloudflare.Env>;
