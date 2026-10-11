import { eq } from "drizzle-orm";
import type { Database } from "../database.ts";
import { items } from "../schema.ts";

export type ItemChanges = Partial<Omit<typeof items.$inferInsert, "id" | "updated_at">>;

export const updateItem = (db: Database, id: string, changes: ItemChanges) =>
  db
    .update(items)
    .set({ ...changes, updated_at: new Date().toISOString() })
    .where(eq(items.id, id));
