import * as v from "valibot";
import type { ElementPath } from "./paths.ts";
import type { AnnotatedUnit, Unit } from "./units.ts";

export const INVENTORY_ROLES = ["unit", "inline", "wrapper", "title"] as const;
export type InventoryRole = (typeof INVENTORY_ROLES)[number];

export const ignoreSchema = v.object({
  selector: v.string(),
  reason: v.string(),
});

export const inventorySchema = v.object({
  selector: v.string(),
  role: v.picklist(INVENTORY_ROLES),
});

export type IgnoreDeclaration = v.InferOutput<typeof ignoreSchema>;
export type InventoryDeclaration = v.InferOutput<typeof inventorySchema>;

export const declarationsSchema = v.object({
  container: v.pipe(v.string(), v.minLength(1)),
  extract: v.function(),
  ignores: v.optional(v.array(ignoreSchema), []),
  inventory: v.optional(v.array(inventorySchema), []),
});

export type Declarations = v.InferOutput<typeof declarationsSchema>;

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

export type RecipeExtract = ($: unknown, toMarkdown: (element: unknown) => string) => RawExtraction;

export interface RecipeModule extends Omit<Declarations, "extract"> {
  extract: RecipeExtract;
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

export type RecipeRun =
  | { ok: true; title: string; units: Unit[] }
  | { ok: false; report: string[] };
