import type { CodeUnit, ParagraphUnit } from "@nagara/common";
import type { Unit as RecipeUnit } from "../runtime/units.ts";
import { toSpoken } from "./derive.ts";

export type DeclaredImage = {
  after: number;
  src: string;
  alt: string;
};

// The synthesizer produces no audio for a paragraph made only of a symbol and fails the whole call
// on it, so a unit whose spoken form carries no letter or digit never becomes a typed unit.
export const isUnspeakable = (spoken: string) => !/[\p{L}\p{N}]/u.test(spoken);

// Runs in document order because each image anchors to the last text unit kept so far: a dropped
// unit hands its images to the kept unit before it, and an image before every kept unit leads
// the list (after = -1).
export const toTypedUnits = (recipeUnits: RecipeUnit[]) => {
  const units: (ParagraphUnit | CodeUnit)[] = [];
  const declaredImages: DeclaredImage[] = [];

  for (const unit of recipeUnits) {
    if (unit.type === "image") {
      declaredImages.push({ after: units.length - 1, src: unit.src, alt: unit.alt });

      continue;
    }

    const spoken = toSpoken(unit.display);

    if (!isUnspeakable(spoken)) {
      units.push({ type: unit.type, display: unit.display, spoken });
    }
  }

  return { units, declaredImages };
};
