import { ITEM_STATUS, type ItemRow } from "@nagara/common";

type QueuedItem = Pick<ItemRow, "url" | "voice">;

const mintItemId = () => `itm_${crypto.randomUUID().replaceAll("-", "").slice(0, 8)}`;

export const insertQueued = async (db: D1Database, { url, voice }: QueuedItem) => {
  const id = mintItemId();
  const now = new Date().toISOString();

  await db
    .prepare(
      "INSERT INTO items (id, url, voice, status, created_at, updated_at, queued_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
    )
    .bind(id, url, voice, ITEM_STATUS.queued, now, now, now)
    .run();

  return id;
};
