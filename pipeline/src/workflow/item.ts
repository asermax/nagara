import { WorkflowEntrypoint, type WorkflowEvent, type WorkflowStep } from "cloudflare:workers";
import type { ItemWorkflowParams } from "@nagara/common";
import { fetchStep } from "./steps/fetch.ts";
import { imagesStep } from "./steps/images.ts";
import { leaseStep, releaseStep } from "./steps/lease.ts";
import { recipeStep } from "./steps/recipe.ts";
import type { StepContext } from "./wrapper.ts";

// The lease covers exactly the recipe: it is asked for before it and given back right after it.
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
  }
}
