import type { RecipeVersionRow } from "../../recipe.ts";
import type { Database } from "../database.ts";
import { recipeVersions } from "../schema.ts";
import { getLatestRecipeVersion } from "./get-latest-recipe-version.ts";

type NewRecipeVersion = Pick<RecipeVersionRow, "domain" | "script">;

// A revision is a pure insert at the next version; the unique (domain, version) pair turns two
// concurrent saves into one failure rather than two rows with one number.
export const createRecipeVersion = async (db: Database, { domain, script }: NewRecipeVersion) =>
  db
    .insert(recipeVersions)
    .values({
      domain,
      version: ((await getLatestRecipeVersion(db, domain))?.version ?? 0) + 1,
      script,
    })
    .returning()
    .get();
