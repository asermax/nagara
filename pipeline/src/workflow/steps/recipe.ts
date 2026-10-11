import { NonRetryableError } from "cloudflare:workflows";
import {
  createRecipeVersion,
  database,
  getLatestRecipeVersion,
  STEP,
  updateItem,
} from "@nagara/common";
import { settle } from "../../recipes/settle.ts";
import { toTypedUnits } from "../../spoken/typed-units.ts";
import { runStep, type StepContext } from "../wrapper.ts";

// A verdict or a run that gave up has already used the agents' own retries, so it fails the item
// at once rather than starting the agents over on the step's next attempt.
export const recipeStep = (ctx: StepContext, domain: string, html: string) =>
  runStep(ctx, STEP.recipe, "generating", "15 minutes", async () => {
    const { env, itemId, instanceId } = ctx;
    const db = database(env.DB);
    const recipe = await getLatestRecipeVersion(db, domain);
    const settled = await settle(env, { instanceId, domain, html, recipe });

    if (settled.kind === "not-article") {
      throw new NonRetryableError("the page is not an article");
    }

    if (settled.kind === "gave-up") {
      throw new NonRetryableError(settled.reason);
    }

    const { units, declaredImages } = toTypedUnits(settled.units);

    await updateItem(db, itemId, {
      title: settled.title,
      units,
      recipe_version_id:
        settled.versionId ?? (await createRecipeVersion(db, { domain, script: settled.script })),
    });

    return { declaredImages };
  });
