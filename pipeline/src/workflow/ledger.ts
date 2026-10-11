import { type CostEntryRow, encodeJson } from "@nagara/common";

export type CostEntry = Pick<CostEntryRow, "item_id" | "type" | "quantity" | "unit" | "dollars"> &
  Partial<Pick<CostEntryRow, "cached" | "detail">>;

export const ledgerInsert = (db: D1Database, entry: CostEntry) =>
  db
    .prepare(
      `INSERT INTO cost_entries (id, item_id, type, quantity, unit, dollars, cached, detail, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .bind(
      `cst_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`,
      entry.item_id,
      entry.type,
      entry.quantity,
      entry.unit,
      entry.dollars,
      entry.cached ? 1 : 0,
      encodeJson(entry.detail),
      new Date().toISOString(),
    );
