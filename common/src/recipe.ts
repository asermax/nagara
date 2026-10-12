import type { recipeVersions } from "./db/schema.ts";

export type RecipeVersionRow = typeof recipeVersions.$inferSelect;
