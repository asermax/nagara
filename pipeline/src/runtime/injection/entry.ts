import { load as loadCheerio } from "cheerio/slim";
import type { Element } from "domhandler";
import * as v from "valibot";
import { describeError } from "../../errors.ts";
import { pathOf } from "../paths.ts";
import {
  type Declarations,
  declarationsSchema,
  type ExecutionPayload,
  type RawUnit,
  type RecipeExtract,
  type RecipeModule,
  type SerializedExtraction,
} from "../recipe.ts";
import { type AnnotatedUnit, UNIT_TYPES } from "../units.ts";
import { toMarkdown } from "./markdown.ts";

function elementOf(value: unknown): Element | null {
  if (value == null) {
    return null;
  }
  if (Array.isArray(value)) {
    return (value[0] as Element) ?? null;
  }
  if (typeof value === "object" && "0" in (value as Record<string, unknown>)) {
    const first = Object.values(value as Record<string, unknown>)[0] as Element;
    return first ?? null;
  }
  return value as Element;
}

function parseDeclarations(
  recipe: Partial<RecipeModule>,
): { ok: true; declarations: Declarations } | { ok: false; report: string[] } {
  const parsed = v.safeParse(declarationsSchema, recipe);
  if (parsed.success) {
    return { ok: true, declarations: parsed.output };
  }
  return {
    ok: false,
    report: [
      `the recipe's declarations are malformed: ${parsed.issues
        .slice(0, 3)
        .map((issue) => `${v.getDotPath(issue) ?? "recipe"} ${issue.message}`)
        .join("; ")}`,
    ],
  };
}

function annotateUnits(rawUnits: RawUnit[]): AnnotatedUnit[] {
  const units: AnnotatedUnit[] = [];
  rawUnits.forEach((unit, position) => {
    if (!UNIT_TYPES.includes(unit.type as never)) {
      throw new Error(
        `unit ${position} has type "${unit.type}"; expected one of ${UNIT_TYPES.join(", ")}`,
      );
    }
    const element = elementOf(unit.element);
    if (element == null) {
      throw new Error(`unit ${position} does not carry the element it was extracted from`);
    }
    if (unit.type === "image") {
      if (typeof unit.src !== "string") {
        throw new Error(`image unit ${position} does not carry the src the page presents`);
      }
      units.push({
        type: "image",
        display: typeof unit.alt === "string" ? unit.alt : "",
        src: unit.src,
        alt: typeof unit.alt === "string" ? unit.alt : "",
        path: pathOf(element),
      });
      return;
    }
    if (typeof unit.display !== "string") {
      throw new Error(`unit ${position} does not carry the display markdown`);
    }
    units.push({
      type: unit.type as AnnotatedUnit["type"],
      display: unit.display,
      path: pathOf(element),
    });
  });
  return units;
}

export async function execute(
  recipeModule: Promise<unknown>,
  html: string,
): Promise<ExecutionPayload> {
  try {
    const recipe = (await recipeModule) as Partial<RecipeModule>;
    const parsed = parseDeclarations(recipe);
    if (!parsed.ok) {
      return { ok: false, report: parsed.report };
    }
    const { declarations } = parsed;
    const $ = loadCheerio(html);
    const container = $(declarations.container).first();
    const containerElement = container.get(0) as Element | undefined;
    if (containerElement == null) {
      return {
        ok: false,
        report: [
          `the container selector "${declarations.container}" matches nothing in the article`,
        ],
      };
    }
    const output = (declarations.extract as RecipeExtract)($, toMarkdown);
    if (output == null || typeof output.title !== "string") {
      return { ok: false, report: ["extract($) did not return a title"] };
    }
    if (!Array.isArray(output.units)) {
      return { ok: false, report: ["extract($) did not return a list of units"] };
    }
    const units = annotateUnits(output.units);
    const extraction: SerializedExtraction = {
      title: output.title,
      units,
      containerPath: pathOf(containerElement),
      ignores: declarations.ignores,
      inventory: declarations.inventory,
    };
    return { ok: true, extraction };
  } catch (error) {
    return { ok: false, report: [`the recipe crashed: ${describeError(error)}`] };
  }
}
