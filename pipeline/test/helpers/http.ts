import { introspectWorkflowInstance, runInDurableObject } from "cloudflare:test";
import { env, exports } from "cloudflare:workers";
import { expect } from "vitest";
import type { JobStatusBody } from "../../src/http/job-status.ts";
import { domainQueueStub } from "../../src/queue/domain-queue.ts";
import { articleHtml } from "../fixtures/article.ts";

export interface PostJobBody {
  html?: string;
  recipe?: string;
  job_id?: string;
  domain?: string;
  [key: string]: unknown;
}

export async function postJob(body: PostJobBody): Promise<Response> {
  return await exports.default.fetch(
    new Request("https://pipeline.test/jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ html: articleHtml, ...body }),
    }),
  );
}

export async function getJob(jobId: string): Promise<JobStatusBody> {
  const response = await exports.default.fetch(new Request(`https://pipeline.test/jobs/${jobId}`));
  expect(response.status).toBe(200);
  return (await response.json()) as JobStatusBody;
}

export function queueFor(domain: string) {
  return domainQueueStub(env, domain);
}

export async function readLease(domain: string): Promise<{ jobId: string } | undefined> {
  return await runInDurableObject(queueFor(domain), (_instance, state) =>
    state.storage.get<{ jobId: string }>("lease"),
  );
}

export async function readWaiting(domain: string): Promise<string[]> {
  const waiting = (await runInDurableObject(queueFor(domain), (_instance, state) =>
    state.storage.get<{ jobId: string }[]>("waiting"),
  )) as { jobId: string }[];
  return waiting.map((entry) => entry.jobId);
}

export async function holdLease(domain: string, jobId: string): Promise<void> {
  await runInDurableObject(queueFor(domain), (_instance, state) =>
    state.storage.put("lease", { jobId }),
  );
}

export async function armAlarm(domain: string): Promise<void> {
  await runInDurableObject(queueFor(domain), (_instance, state) =>
    state.storage.setAlarm(Date.now() + 60000),
  );
}

export async function runToTerminal(jobId: string): Promise<JobStatusBody> {
  await using instance = await introspectWorkflowInstance(env.EXTRACTION, jobId);
  await instance.waitForStatus("complete");
  return (await instance.getOutput()) as JobStatusBody;
}
