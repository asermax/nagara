import { and, eq, lt } from "drizzle-orm";
import { ITEM_STATUS } from "../../item.ts";
import type { Database } from "../database.ts";
import { items } from "../schema.ts";

export const claimRequeue = async (db: Database, id: string, staleBefore: string) =>
  (await db
    .update(items)
    .set({ queued_at: new Date().toISOString() })
    .where(
      and(eq(items.id, id), eq(items.status, ITEM_STATUS.queued), lt(items.queued_at, staleBefore)),
    )
    .returning()
    .get()) ?? null;
