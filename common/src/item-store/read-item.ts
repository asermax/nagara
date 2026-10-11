import type { ItemRow } from "../item.ts";
import { decodeJson } from "./json-column.ts";

type StoredItemRow = Omit<ItemRow, "units" | "degradations"> & {
  units: string | null;
  degradations: string | null;
};

export const readItem = async (db: D1Database, id: string): Promise<ItemRow | null> => {
  const row = await db.prepare("SELECT * FROM items WHERE id = ?").bind(id).first<StoredItemRow>();

  if (row == null) {
    return null;
  }

  return {
    ...row,
    units: decodeJson(row.units),
    degradations: decodeJson(row.degradations),
  };
};
