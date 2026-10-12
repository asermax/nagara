import { desc, eq } from "drizzle-orm";
import type { Database } from "../database.ts";
import { recipeVersions } from "../schema.ts";

export const getLatestRecipeVersion = async (db: Database, domain: string) =>
  (await db
    .select()
    .from(recipeVersions)
    .where(eq(recipeVersions.domain, domain))
    .orderBy(desc(recipeVersions.version))
    .limit(1)
    .get()) ?? null;
