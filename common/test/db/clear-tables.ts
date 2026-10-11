import { env } from "cloudflare:workers";
import { database } from "../../src/db/database.ts";
import { costEntries, items, recipeVersions } from "../../src/db/schema.ts";

export const clearTables = async () => {
  const db = database(env.DB);

  await db.batch([db.delete(costEntries), db.delete(items), db.delete(recipeVersions)]);
};
