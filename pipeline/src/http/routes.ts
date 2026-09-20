import * as v from "valibot";
import { describeError } from "../errors.ts";
import { domainQueueStub, type EnqueueResult } from "../queue/domain-queue.ts";
import { readJobStatus } from "./read.ts";

const JOB_ID_CLASS = "[a-zA-Z0-9_][a-zA-Z0-9-_]*";

const JOB_ID_PATTERN = new RegExp(`^${JOB_ID_CLASS}$`);

const JOB_ROUTE_PATTERN = new RegExp(`^/jobs/(${JOB_ID_CLASS})$`);

const createBody = v.object({
  html: v.pipe(v.string(), v.minLength(1)),
  recipe: v.optional(v.string()),
  job_id: v.pipe(v.string(), v.regex(JOB_ID_PATTERN)),
  domain: v.pipe(v.string(), v.minLength(1)),
});

function json(body: unknown, status: number): Response {
  return Response.json(body, { status });
}

// UTF-8 length is bounded by the string length on both sides, so most
// requests are decided without encoding anything.
const encoder = new TextEncoder();

function exceedsCap(html: string, cap: number): boolean {
  if (html.length > cap) {
    return true;
  }
  if (3 * html.length <= cap) {
    return false;
  }
  return encoder.encode(html).length > cap;
}

async function handleCreate(request: Request, env: Cloudflare.Env): Promise<Response> {
  let parsed: v.SafeParseResult<typeof createBody>;
  try {
    parsed = v.safeParse(createBody, await request.json());
  } catch {
    return json({ error: "the body is not json" }, 400);
  }
  if (!parsed.success) {
    return json({ error: "the create body is malformed" }, 400);
  }
  const { html, recipe, job_id, domain } = parsed.output;
  if (exceedsCap(html, env.maxHtmlBytes)) {
    return json({ error: `the html is over the ${env.maxHtmlBytes} byte cap` }, 413);
  }
  let outcome: EnqueueResult;
  try {
    outcome = await domainQueueStub(env, domain).enqueue(job_id, { html, recipe, domain });
  } catch (error) {
    return json({ error: describeError(error) }, 500);
  }
  if ("conflict" in outcome) {
    return json({ error: "the job id already exists" }, 409);
  }
  return json({ state: outcome.created ? "running" : "queued" }, 201);
}

export default {
  async fetch(request: Request, env: Cloudflare.Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/jobs") {
      return await handleCreate(request, env);
    }
    const match = url.pathname.match(JOB_ROUTE_PATTERN);
    if (request.method === "GET" && match != null) {
      return json(await readJobStatus(env, match[1]), 200);
    }
    return new Response("not found", { status: 404 });
  },
};
