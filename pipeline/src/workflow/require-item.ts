import { NonRetryableError } from "cloudflare:workflows";
import { type Database, getItem } from "@nagara/common";

export const requireItem = async (db: Database, itemId: string) => {
  const item = await getItem(db, itemId);

  if (item == null) {
    throw new NonRetryableError(`item ${itemId} has no row`);
  }

  return item;
};
