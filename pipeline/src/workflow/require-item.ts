import { NonRetryableError } from "cloudflare:workflows";
import { readItem } from "@nagara/common";

export const requireItem = async (db: D1Database, itemId: string) => {
  const item = await readItem(db, itemId);

  if (item == null) {
    throw new NonRetryableError(`item ${itemId} has no row`);
  }

  return item;
};
