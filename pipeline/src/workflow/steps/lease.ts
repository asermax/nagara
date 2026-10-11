import { STEP } from "@nagara/common";
import { domainQueueStub, LEASE_GRANTED } from "../../queue/domain-queue.ts";
import { failStep, runStep, type StepContext } from "../wrapper.ts";

const LEASE_WAITS = 3;

// Copied out of the RPC result, which carries a disposer a step result cannot hold.
const askForLease = async ({ env, instanceId }: StepContext, domain: string) => {
  const { granted } = await domainQueueStub(env, domain).acquire(instanceId);

  return { granted };
};

// The waits sit between steps and write nothing, so current_step reads lease throughout. A grant
// can be lost to a deploy, so each wait that times out is followed by asking again.
export const leaseStep = async (ctx: StepContext, domain: string) => {
  const { granted } = await runStep(ctx, STEP.lease, "queued", "1 minute", () =>
    askForLease(ctx, domain),
  );

  if (granted) {
    return;
  }

  for (let wait = 1; wait <= LEASE_WAITS; wait += 1) {
    try {
      await ctx.step.waitForEvent(`lease wait ${wait}`, {
        type: LEASE_GRANTED,
        timeout: "5 minutes",
      });

      return;
    } catch {
      const recheck = await ctx.step.do(`lease recheck ${wait}`, () => askForLease(ctx, domain));

      if (recheck.granted) {
        return;
      }
    }
  }

  const error = new Error(`the domain's lease was not granted after ${LEASE_WAITS} waits`);

  await failStep(ctx, STEP.lease, error);

  throw error;
};

export const releaseStep = (ctx: StepContext, domain: string) =>
  runStep(ctx, STEP.release, "generating", "1 minute", async () => {
    await domainQueueStub(ctx.env, domain).release(ctx.instanceId);
  });
