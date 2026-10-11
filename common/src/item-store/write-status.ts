import type { ItemStatus } from "../item.ts";
import type { Step } from "../workflow.ts";

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
