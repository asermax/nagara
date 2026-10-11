import { eq } from "drizzle-orm";
import type { Database } from "../database.ts";
import { items } from "../schema.ts";

export const getItem = async (db: Database, id: string) =>
  (await db.select().from(items).where(eq(items.id, id)).get()) ?? null;
