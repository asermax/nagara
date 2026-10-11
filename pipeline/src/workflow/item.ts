import { WorkflowEntrypoint, type WorkflowEvent, type WorkflowStep } from "cloudflare:workers";
import type { ItemWorkflowParams } from "@nagara/common";
import { describeStep } from "./steps/describe.ts";
import { fetchStep } from "./steps/fetch.ts";
import { imagesStep } from "./steps/images.ts";
import { leaseStep, releaseStep } from "./steps/lease.ts";
import { recipeStep } from "./steps/recipe.ts";
import type { StepContext } from "./wrapper.ts";

// The order is required throughout: the lease covers exactly the recipe, images come before
// describe because describe reads the stored images.
export class ItemWorkflow extends WorkflowEntrypoint<Cloudflare.Env, ItemWorkflowParams> {
  async run(event: WorkflowEvent<ItemWorkflowParams>, step: WorkflowStep) {
    const ctx: StepContext = {
      step,
      env: this.env,
      itemId: event.payload.itemId,
      instanceId: event.instanceId,
    };

    const { html } = await fetchStep(ctx);

    await leaseStep(ctx);

    const { declaredImages } = await recipeStep(ctx, html);

    await releaseStep(ctx);

    await imagesStep(ctx, declaredImages);
    await describeStep(ctx);
  }
}
