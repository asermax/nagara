import {
  DEGRADATION_REASON,
  type Degradation,
  type DegradationReason,
  encodeJson,
  STEP,
  type Unit,
} from "@nagara/common";
import { describeOne } from "../../describe/describe-one.ts";
import { type DescribeJob, describeJobs } from "../../describe/jobs.ts";
import { ledgerInsert } from "../ledger.ts";
import { requireItem } from "../require-item.ts";
import { runStep, STEP_RETRIES, type StepContext } from "../wrapper.ts";

const CODE_FLOOR = "Code with no description.";

// A code unit floors; an image keeps the fallback acquisition gave it (its alt, or the image
// floor), so a description that fails never goes silent.
const fallBack = (
  units: Unit[],
  degradations: Degradation[],
  job: DescribeJob,
  reason: DegradationReason,
) => {
  if (job.kind === "code") {
    units[job.index] = { ...units[job.index], spoken: CODE_FLOOR };
  }

  degradations.push({ type: job.kind, reason });
};

// The children only return their results, so this step is the one writer of the units column and
// the row changes once. A child that fails every attempt degrades its unit and never fails the
// step.
export const describeStep = (ctx: StepContext) =>
  runStep(ctx, STEP.describe, "generating", "5 minutes", async () => {
    const { step, env, itemId } = ctx;
    const item = await requireItem(env.DB, itemId);
    const units = [...(item.units ?? [])];
    const degradations = [...(item.degradations ?? [])];
    const { described, capped } = describeJobs(units, item.title, env.describeMaxPerItem);
    const outcomes = await Promise.allSettled(
      described.map((job) =>
        step.do(`describe ${job.index}`, { retries: STEP_RETRIES, timeout: "1 minute" }, () =>
          describeOne(env, item.units ?? [], item.title, job),
        ),
      ),
    );
    const ledger: D1PreparedStatement[] = [];

    outcomes.forEach((outcome, position) => {
      const job = described[position];

      if (outcome.status === "rejected") {
        fallBack(units, degradations, job, DEGRADATION_REASON.describeFailed);

        return;
      }

      units[job.index] = {
        ...units[job.index],
        spoken: `${job.kind === "code" ? "Code" : "Image"}: ${outcome.value.spoken}`,
      };
      ledger.push(
        ledgerInsert(env.DB, {
          item_id: itemId,
          type: "describer",
          quantity: 1,
          unit: "calls",
          dollars: env.describerDollarsPerCall,
          cached: outcome.value.cached,
          detail: { kind: job.kind },
        }),
      );
    });

    for (const job of capped) {
      fallBack(units, degradations, job, DEGRADATION_REASON.describeCapReached);
    }

    await env.DB.batch([
      env.DB.prepare(
        "UPDATE items SET units = ?, degradations = ?, updated_at = ? WHERE id = ?",
      ).bind(
        encodeJson(units),
        encodeJson(degradations.length === 0 ? null : degradations),
        new Date().toISOString(),
        itemId,
      ),
      ...ledger,
    ]);
  });
