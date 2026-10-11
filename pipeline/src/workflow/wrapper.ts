import type { WorkflowStep, WorkflowStepConfig } from "cloudflare:workers";
import { type ItemStatus, type Step, writeStatus } from "@nagara/common";

export type StepContext = {
  step: WorkflowStep;
  env: Cloudflare.Env;
  itemId: string;
  instanceId: string;
};

// The limit counts retries, not attempts: 2 gives each step the three attempts the item lifecycle
// promises.
export const STEP_RETRIES: WorkflowStepConfig["retries"] = {
  limit: 2,
  delay: "5 seconds",
  backoff: "exponential",
};

// step.do rethrows a NonRetryableError as a plain Error whose message carries the class name; the
// row keeps the step's own words.
const messageOf = (error: unknown) =>
  (error instanceof Error ? error.message : String(error)).replace(/^NonRetryableError: /, "");

export const failStep = async ({ step, env, itemId }: StepContext, name: Step, error: unknown) => {
  await step.do(`${name} failed`, async () => {
    await writeStatus(env.DB, itemId, {
      status: "failed",
      currentStep: name,
      error: messageOf(error),
    });
  });
};

// The status write happens inside every attempt, so a restart from this step writes it again and
// clears the error the failed run left. An attempt that fails with attempts left writes nothing,
// so the row never shows failed while the step still retries.
export const runStep = async <T extends Rpc.Serializable<T>>(
  ctx: StepContext,
  name: Step,
  status: Extract<ItemStatus, "queued" | "generating">,
  timeout: WorkflowStepConfig["timeout"],
  body: () => Promise<T>,
) => {
  try {
    return await ctx.step.do(name, { retries: STEP_RETRIES, timeout }, async () => {
      await writeStatus(ctx.env.DB, ctx.itemId, { status, currentStep: name });

      return body();
    });
  } catch (error) {
    await failStep(ctx, name, error);

    throw error;
  }
};
