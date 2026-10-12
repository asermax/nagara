import { eq } from "drizzle-orm";
import type { Database } from "../database.ts";
import { items } from "../schema.ts";

export type ItemChanges = Partial<Omit<typeof items.$inferInsert, "id" | "updated_at">>;

export const updateItem = async (db: Database, id: string, changes: ItemChanges) =>
  (await db.update(items).set(changes).where(eq(items.id, id)).returning().get()) ?? null;
