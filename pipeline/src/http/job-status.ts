import * as v from "valibot";
import { unitSchema } from "../runtime/units.ts";

export const JOB_STATES = ["queued", "running", "complete", "not_article", "error"] as const;

const jobStatusBody = v.object({
  state: v.picklist(JOB_STATES),
  title: v.optional(v.string()),
  units: v.optional(v.array(unitSchema)),
  recipe: v.optional(v.string()),
  error: v.optional(v.string()),
});

export type JobStatusBody = v.InferOutput<typeof jobStatusBody>;

export function parseJobStatusBody(value: unknown): JobStatusBody | null {
  const parsed = v.safeParse(jobStatusBody, value);
  return parsed.success ? parsed.output : null;
}
