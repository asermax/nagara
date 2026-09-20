import { domainQueueStub } from "../queue/domain-queue.ts";
import { jobIndexStub } from "../queue/job-index.ts";
import type { JobStatusBody } from "./job-status.ts";
import { parseJobStatusBody } from "./job-status.ts";

function mapInstanceStatus(status: InstanceStatus): JobStatusBody {
  switch (status.status) {
    case "complete": {
      const output = parseJobStatusBody(status.output);
      if (output != null) {
        return output;
      }
      return { state: "error", error: "the workflow returned an unreadable output" };
    }
    case "errored":
      return { state: "error", error: status.error?.message ?? "the workflow instance errored" };
    case "terminated":
      return { state: "error", error: "the workflow instance was terminated" };
    default:
      return { state: "running" };
  }
}

async function readThroughIndex(env: Cloudflare.Env, jobId: string): Promise<JobStatusBody> {
  const domain = await jobIndexStub(env).domainOf(jobId);
  if (domain == null) {
    return { state: "error", error: "unknown job id" };
  }
  const state = await domainQueueStub(env, domain).stateOf(jobId);
  if (state === "queued" || state === "running") {
    return { state };
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
