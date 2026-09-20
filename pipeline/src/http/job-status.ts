import type { Unit } from "../runtime/units.ts";

export const JOB_STATES = ["queued", "running", "complete", "not_article", "error"] as const;
export type JobState = (typeof JOB_STATES)[number];

export interface JobStatusBody {
  state: JobState;
  title?: string;
  units?: Unit[];
  recipe?: string;
  error?: string;
}

export function isJobStatusBody(value: unknown): value is JobStatusBody {
  if (typeof value !== "object" || value == null) {
    return false;
  }
  return JOB_STATES.includes((value as JobStatusBody).state as never);
}
