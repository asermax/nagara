import type { Degradation, Unit } from "./units.ts";
import type { Step } from "./workflow.ts";

export const ITEM_STATUS = {
  queued: "queued",
  generating: "generating",
  ready: "ready",
  failed: "failed",
} as const;

export type ItemStatus = (typeof ITEM_STATUS)[keyof typeof ITEM_STATUS];

export type ItemRow = {
  id: string;
  url: string;
  title: string | null;
  voice: string;
  status: ItemStatus;
  created_at: string;
  updated_at: string;
  queued_at: string;
  workflow_instance_id: string | null;
  current_step: Step | null;
  extraction_domain: string | null;
  recipe_version_id: string | null;
  retry_count: number;
  duration: number | null;
  audio_format: string | null;
  units: Unit[] | null;
  degradations: Degradation[] | null;
  error: string | null;
};
