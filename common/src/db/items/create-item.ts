import { ITEM_STATUS, type ItemRow } from "../../item.ts";
import type { Database } from "../database.ts";
import { items } from "../schema.ts";

type QueuedItem = Pick<ItemRow, "url" | "voice">;

export const createItem = (db: Database, { url, voice }: QueuedItem) =>
  db.insert(items).values({ url, voice, status: ITEM_STATUS.queued }).returning().get();
