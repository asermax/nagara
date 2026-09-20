import type { ElementPath } from "../runtime/paths.ts";

export const UNIT_TYPES = ["paragraph", "code", "image"] as const;
export type UnitType = (typeof UNIT_TYPES)[number];

export interface TextUnit {
  type: "paragraph" | "code";
  display: string;
}

export interface ImageUnit {
  type: "image";
  display: string;
  src: string;
  alt: string;
}

export type Unit = TextUnit | ImageUnit;

export interface AnnotatedUnit {
  type: UnitType;
  display: string;
  src?: string;
  alt?: string;
  path: ElementPath;
}

export function toBoundaryUnit(unit: AnnotatedUnit): Unit {
  if (unit.type === "image") {
    return { type: "image", display: unit.display, src: unit.src ?? "", alt: unit.alt ?? "" };
  }
  return { type: unit.type, display: unit.display };
}
