import { NonRetryableError } from "cloudflare:workflows";
import { encodeJson, STEP } from "@nagara/common";
import { settle } from "../../recipes/settle.ts";
import { currentRecipe, saveVersion } from "../../recipes/store.ts";
import { toTypedUnits } from "../../spoken/typed-units.ts";
import { runStep, type StepContext } from "../wrapper.ts";

// A verdict or a run that gave up has already used the agents' own retries, so it fails the item
// at once rather than starting the agents over on the step's next attempt.
export const recipeStep = (ctx: StepContext, domain: string, html: string) =>
  runStep(ctx, STEP.recipe, "generating", "15 minutes", async () => {
    const { env, itemId, instanceId } = ctx;
    const recipe = await currentRecipe(env.DB, domain);
    const settled = await settle(env, { instanceId, domain, html, recipe });

    if (settled.kind === "not-article") {
      throw new NonRetryableError("the page is not an article");
    }

    if (settled.kind === "gave-up") {
      throw new NonRetryableError(settled.reason);
    }

    const { units, declaredImages } = toTypedUnits(settled.units);
    const recipeVersionId =
      settled.versionId ?? (await saveVersion(env.DB, domain, settled.script));

    await env.DB.prepare(
      "UPDATE items SET title = ?, units = ?, recipe_version_id = ?, updated_at = ? WHERE id = ?",
    )
      .bind(settled.title, encodeJson(units), recipeVersionId, new Date().toISOString(), itemId)
      .run();

    return { declaredImages };
  });
