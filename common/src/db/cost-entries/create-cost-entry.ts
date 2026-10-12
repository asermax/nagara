import type { Database } from "../database.ts";
import { costEntries } from "../schema.ts";

export type NewCostEntry = Omit<typeof costEntries.$inferInsert, "id" | "created_at">;

export type ItemCost = Omit<NewCostEntry, "item_id">;

export const createCostEntry = (db: Database, entry: NewCostEntry) =>
  db.insert(costEntries).values(entry).returning().get();
