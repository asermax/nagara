import { env } from "cloudflare:workers";
import { asc, eq } from "drizzle-orm";
import { database } from "../../../src/db/database.ts";
import { costEntries } from "../../../src/db/schema.ts";

export const costsOf = (itemId: string) =>
  database(env.DB)
    .select()
    .from(costEntries)
    .where(eq(costEntries.item_id, itemId))
    .orderBy(asc(costEntries.created_at));
