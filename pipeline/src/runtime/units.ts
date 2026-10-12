import * as v from "valibot";
import type { ElementPath } from "./paths.ts";

export const UNIT_TYPES = ["paragraph", "code", "image"] as const;

export const unitSchema = v.variant("type", [
  v.object({
    type: v.picklist(["paragraph", "code"]),
    display: v.string(),
  }),
  v.object({
    type: v.literal("image"),
    src: v.string(),
    alt: v.string(),
  }),
]);

export type Unit = v.InferOutput<typeof unitSchema>;

export type AnnotatedUnit =
  | { type: "paragraph" | "code"; display: string; path: ElementPath }
  | { type: "image"; src: string; alt: string; path: ElementPath };

export function toBoundaryUnit(unit: AnnotatedUnit): Unit {
  if (unit.type === "image") {
    return { type: "image", src: unit.src, alt: unit.alt };
  }
  return { type: unit.type, display: unit.display };
}
