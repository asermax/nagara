import type { ItemStatus } from "../../item.ts";
import type { Step } from "../../workflow.ts";
import type { Database } from "../database.ts";
import { updateItem } from "./update-item.ts";

export type StatusWrite =
  | { status: Exclude<ItemStatus, "ready" | "failed">; currentStep: Step | null }
  | { status: Extract<ItemStatus, "failed">; currentStep: Step | null; error: string };

export const writeStatus = (db: Database, id: string, write: StatusWrite) =>
  updateItem(db, id, {
    status: write.status,
    current_step: write.currentStep,
    error: write.status === "failed" ? write.error : null,
  });
