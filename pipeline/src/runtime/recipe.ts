import type { ElementPath } from "./paths.ts";
import type { AnnotatedUnit } from "./units.ts";

export const INVENTORY_ROLES = ["unit", "inline", "wrapper", "title"] as const;
export type InventoryRole = (typeof INVENTORY_ROLES)[number];

export interface IgnoreDeclaration {
  selector: string;
  reason: string;
}

export interface InventoryDeclaration {
  selector: string;
  role: InventoryRole;
}

export interface RawUnit {
  type: string;
  display?: string;
  src?: string;
  alt?: string;
  element: unknown;
}

export interface RawExtraction {
  title: string;
  units: RawUnit[];
}

export interface RecipeModule {
  container: string;
  ignores: IgnoreDeclaration[];
  inventory: InventoryDeclaration[];
  extract: ($: unknown, toMarkdown: (element: unknown) => string) => RawExtraction;
}

export interface SerializedExtraction {
  title: string;
  units: AnnotatedUnit[];
  containerPath: ElementPath;
  ignores: IgnoreDeclaration[];
  inventory: InventoryDeclaration[];
}

export type ExecutionPayload =
  | { ok: true; extraction: SerializedExtraction }
  | { ok: false; report: string[] };

export interface RecipeRun {
  ok: boolean;
  title?: string;
  units?: import("./units.ts").Unit[];
  report?: string[];
}
