import { readJobStatus } from "./read.ts";

const JOB_ID_PATTERN = /^[a-zA-Z0-9_][a-zA-Z0-9-_]*$/;

function json(body: unknown, status: number): Response {
  return Response.json(body, { status });
}

interface CreateBody {
  html?: unknown;
  recipe?: unknown;
  job_id?: unknown;
  domain?: unknown;
}

async function handleCreate(request: Request, env: Cloudflare.Env): Promise<Response> {
  let body: CreateBody;
  try {
    body = (await request.json()) as CreateBody;
  } catch {
    return json({ error: "the body is not json" }, 400);
  }
  const { html, recipe, job_id, domain } = body;
  if (typeof html !== "string" || html.length === 0) {
    return json({ error: "html is required" }, 400);
  }
  if (typeof job_id !== "string" || !JOB_ID_PATTERN.test(job_id)) {
    return json({ error: "job_id is malformed" }, 400);
  }
  if (typeof domain !== "string" || domain.length === 0) {
    return json({ error: "domain is required" }, 400);
  }
  if (recipe != null && typeof recipe !== "string") {
    return json({ error: "recipe must be a script string" }, 400);
  }
  const bytes = new TextEncoder().encode(html).length;
  if (bytes > env.maxHtmlBytes) {
    return json(
      { error: `the html is ${bytes} bytes, over the ${env.maxHtmlBytes} byte cap` },
      413,
    );
  }
  const queueId = env.DOMAIN_QUEUE.idFromName(domain);
  const queueResponse = await env.DOMAIN_QUEUE.get(queueId).fetch("https://queue/enqueue", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      job_id,
      params: { html, recipe: recipe ?? undefined, domain },
    }),
  });
  if (queueResponse.status === 409) {
    return json({ error: "the job id already exists" }, 409);
  }
  if (!queueResponse.ok) {
    return json({ error: "the domain queue rejected the job" }, 500);
  }
  const { created } = (await queueResponse.json()) as { created: boolean };
  return json({ state: created ? "running" : "queued" }, 201);
}

export default {
  async fetch(request: Request, env: Cloudflare.Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/jobs") {
      return await handleCreate(request, env);
    }
    const match = url.pathname.match(/^\/jobs\/([a-zA-Z0-9_][a-zA-Z0-9-_]*)$/);
    if (request.method === "GET" && match != null) {
      return json(await readJobStatus(env, match[1]), 200);
    }
    return new Response("not found", { status: 404 });
  },
};
