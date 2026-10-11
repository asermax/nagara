import type { Database } from "../database.ts";
import { mintId } from "../mint-id.ts";
import { costEntries } from "../schema.ts";

export type NewCostEntry = Omit<typeof costEntries.$inferInsert, "id" | "created_at">;

export const createCostEntry = (db: Database, entry: NewCostEntry) =>
  db.insert(costEntries).values({
    ...entry,
    id: mintId("cst", 12),
    created_at: new Date().toISOString(),
  });
