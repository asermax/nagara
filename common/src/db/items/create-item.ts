import { ITEM_STATUS, type ItemRow } from "../../item.ts";
import type { Database } from "../database.ts";
import { mintId } from "../mint-id.ts";
import { items } from "../schema.ts";

type QueuedItem = Pick<ItemRow, "url" | "voice">;

export const createItem = (db: Database, { url, voice }: QueuedItem) => {
  const id = mintId("itm", 8);
  const now = new Date().toISOString();

  return {
    id,
    query: db.insert(items).values({
      id,
      url,
      voice,
      status: ITEM_STATUS.queued,
      created_at: now,
      updated_at: now,
      queued_at: now,
    }),
  };
};
