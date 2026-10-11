import type { ItemRow, ItemStatus } from "./item.ts";
import type { Step } from "./workflow.ts";

export const encodeJson = (value: unknown) => (value == null ? null : JSON.stringify(value));

export const decodeJson = <T>(text: string | null): T | null =>
  text == null ? null : (JSON.parse(text) as T);

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

export type StatusWrite =
  | { status: Exclude<ItemStatus, "ready" | "failed">; currentStep: Step | null }
  | { status: Extract<ItemStatus, "failed">; currentStep: Step | null; error: string };

export const writeStatus = async (db: D1Database, id: string, write: StatusWrite) => {
  await db
    .prepare(
      "UPDATE items SET status = ?, current_step = ?, error = ?, updated_at = ? WHERE id = ?",
    )
    .bind(
      write.status,
      write.currentStep,
      write.status === "failed" ? write.error : null,
      new Date().toISOString(),
      id,
    )
    .run();
};
