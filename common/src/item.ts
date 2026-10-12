import type { items } from "./db/schema.ts";

export const ITEM_STATUS = {
  queued: "queued",
  generating: "generating",
  ready: "ready",
  failed: "failed",
} as const;

export type ItemStatus = (typeof ITEM_STATUS)[keyof typeof ITEM_STATUS];

export type ItemRow = typeof items.$inferSelect;
