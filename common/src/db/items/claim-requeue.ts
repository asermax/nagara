import { and, eq, lt } from "drizzle-orm";
import { ITEM_STATUS } from "../../item.ts";
import type { Database } from "../database.ts";
import { items } from "../schema.ts";

export const claimRequeue = async (db: Database, id: string, staleBefore: string) => {
  const now = new Date().toISOString();

  const claimed = await db
    .update(items)
    .set({ queued_at: now, updated_at: now })
    .where(
      and(eq(items.id, id), eq(items.status, ITEM_STATUS.queued), lt(items.queued_at, staleBefore)),
    )
    .returning({ id: items.id });

  return claimed.length > 0;
};
