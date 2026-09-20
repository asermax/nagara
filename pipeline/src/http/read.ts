import type { JobStatusBody } from "./job-status.ts";
import { isJobStatusBody } from "./job-status.ts";

const JOB_INDEX_NAME = "nagara-job-index";

function mapInstanceStatus(status: InstanceStatus): JobStatusBody {
  switch (status.status) {
    case "complete":
      if (isJobStatusBody(status.output)) {
        return status.output;
      }
      return { state: "error", error: "the workflow returned an unreadable output" };
    case "errored":
      return { state: "error", error: status.error?.message ?? "the workflow instance errored" };
    case "terminated":
      return { state: "error", error: "the workflow instance was terminated" };
    default:
      return { state: "running" };
  }
}

async function readThroughIndex(env: Cloudflare.Env, jobId: string): Promise<JobStatusBody> {
  const indexId = env.JOB_INDEX.idFromName(JOB_INDEX_NAME);
  const indexResponse = await env.JOB_INDEX.get(indexId).fetch(
    `https://index/entries/${encodeURIComponent(jobId)}`,
  );
  if (indexResponse.status === 404) {
    return { state: "error", error: "unknown job id" };
  }
  const { domain } = (await indexResponse.json()) as { domain: string };
  const queueId = env.DOMAIN_QUEUE.idFromName(domain);
  const queueResponse = await env.DOMAIN_QUEUE.get(queueId).fetch(
    `https://queue/state/${encodeURIComponent(jobId)}`,
  );
  const body = (await queueResponse.json()) as { state: string };
  if (body.state === "queued" || body.state === "running") {
    return { state: body.state };
  }
  return { state: "error", error: "unknown job id" };
}

export async function readJobStatus(env: Cloudflare.Env, jobId: string): Promise<JobStatusBody> {
  try {
    const instance = await env.EXTRACTION.get(jobId);
    const status = await instance.status();
    return mapInstanceStatus(status);
  } catch {
    // An id the Workflows API cannot answer means the job has no instance
    // yet: the index says which domain-queue holds it.
  }
  try {
    return await readThroughIndex(env, jobId);
  } catch {
    return { state: "error", error: "the job could not be resolved" };
  }
}
