import {
  createCostEntry,
  DEGRADATION_REASON,
  type DegradationReason,
  database,
  STEP,
  updateItem,
} from "@nagara/common";
import { describeOne } from "../../describe/describe-one.ts";
import { type DescribeJob, describeJobs } from "../../describe/jobs.ts";
import { requireItem } from "../require-item.ts";
import { runStep, STEP_RETRIES, type StepContext } from "../wrapper.ts";

const CODE_FLOOR = "Code with no description.";

// The children only return their results, so this step is the one writer of the units column and
// the row changes once. A child that fails every attempt degrades its unit and never fails the
// step.
export const describeStep = (ctx: StepContext) =>
  runStep(ctx, STEP.describe, "generating", "5 minutes", async () => {
    const { step, env, itemId } = ctx;
    const db = database(env.DB);
    const item = await requireItem(db, itemId);
    const units = [...(item.units ?? [])];
    const degradations = [...(item.degradations ?? [])];

    // A code unit floors; an image keeps the fallback acquisition gave it (its alt, or the image
    // floor), so a description that fails never goes silent.
    const fallBack = (job: DescribeJob, reason: DegradationReason) => {
      if (job.kind === "code") {
        units[job.index] = { ...units[job.index], spoken: CODE_FLOOR };
      }

      degradations.push({ type: job.kind, reason });
    };

    const { described, capped } = describeJobs(units, item.title, env.describeMaxPerItem);
    const outcomes = await Promise.allSettled(
      described.map((job) =>
        step.do(`describe ${job.index}`, { retries: STEP_RETRIES, timeout: "1 minute" }, () =>
          describeOne(env, item.units ?? [], item.title, job),
        ),
      ),
    );
    const ledger: ReturnType<typeof createCostEntry>[] = [];

    outcomes.forEach((outcome, position) => {
      const job = described[position];

      if (outcome.status === "rejected") {
        fallBack(job, DEGRADATION_REASON.describeFailed);

        return;
      }

      units[job.index] = {
        ...units[job.index],
        spoken: `${job.kind === "code" ? "Code" : "Image"}: ${outcome.value.spoken}`,
      };
      ledger.push(
        createCostEntry(db, {
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
      fallBack(job, DEGRADATION_REASON.describeCapReached);
    }

    await db.batch([
      updateItem(db, itemId, {
        units,
        degradations: degradations.length === 0 ? null : degradations,
      }),
      ...ledger,
    ]);
  });
