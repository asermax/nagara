import * as domino from "@mixmark-io/domino";
import { load as loadCheerio } from "cheerio/slim";
import type { Element } from "domhandler";
import TurndownService from "turndown";
import { pathOf } from "../paths.ts";
import {
  type ExecutionPayload,
  type IgnoreDeclaration,
  INVENTORY_ROLES,
  type InventoryDeclaration,
  type InventoryRole,
  type RawUnit,
  type RecipeModule,
  type SerializedExtraction,
} from "../recipe.ts";
import { type AnnotatedUnit, UNIT_TYPES } from "../units.ts";

const turndown = new TurndownService({
  codeBlockStyle: "fenced",
  headingStyle: "atx",
  hr: "---",
  bulletListMarker: "-",
});

// Turndown reaches for browser globals (`document`, `Node`, `NodeFilter`)
// while walking the domino tree; the dynamic worker has none, so the domino
// implementations stand in for them before any conversion runs.
const globals = globalThis as Record<string, unknown>;
globals.document ??= domino.createDocument("<html><body></body></html>");
globals.Node ??= domino.impl.Node;
globals.Element ??= domino.impl.Element;
globals.NodeFilter ??= {
  SHOW_ELEMENT: 1,
  SHOW_TEXT: 4,
  SHOW_COMMENT: 8,
  FILTER_ACCEPT: 1,
  FILTER_REJECT: 2,
  FILTER_SKIP: 3,
};

export function toMarkdown(element: unknown): string {
  const html = renderHtml(element);
  const document = domino.createDocument(`<body>${html}</body>`);
  const markdown = turndown.turndown(document.body);
  return markdown.trim();
}

function renderHtml(element: unknown): string {
  const $ = loadCheerio("");
  return $(element as never).html() ?? "";
}

function describeError(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return String(error);
}

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

function readDeclarations(recipe: Partial<RecipeModule>): ExecutionPayload | null {
  if (typeof recipe.container !== "string" || recipe.container.length === 0) {
    return { ok: false, report: ["the recipe does not export a container selector"] };
  }
  if (typeof recipe.extract !== "function") {
    return { ok: false, report: ["the recipe does not export an extract($) function"] };
  }
  const ignores: IgnoreDeclaration[] = [];
  if (recipe.ignores != null) {
    if (!Array.isArray(recipe.ignores)) {
      return { ok: false, report: ["the recipe's ignores declaration is not a list"] };
    }
    for (const ignore of recipe.ignores) {
      if (
        ignore == null ||
        typeof ignore.selector !== "string" ||
        typeof ignore.reason !== "string"
      ) {
        return { ok: false, report: ["an ignore declaration needs a selector and a reason"] };
      }
      ignores.push({ selector: ignore.selector, reason: ignore.reason });
    }
  }
  const inventory: InventoryDeclaration[] = [];
  if (recipe.inventory != null) {
    if (!Array.isArray(recipe.inventory)) {
      return { ok: false, report: ["the recipe's inventory declaration is not a list"] };
    }
    for (const entry of recipe.inventory) {
      if (
        entry == null ||
        typeof entry.selector !== "string" ||
        !INVENTORY_ROLES.includes(entry.role as InventoryRole)
      ) {
        return {
          ok: false,
          report: [
            `an inventory entry needs a selector and one of the roles ${INVENTORY_ROLES.join(", ")}`,
          ],
        };
      }
      inventory.push({ selector: entry.selector, role: entry.role });
    }
  }
  return null;
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
    const declarationsProblem = readDeclarations(recipe);
    if (declarationsProblem != null) {
      return declarationsProblem;
    }
    const $ = loadCheerio(html);
    const container = $(recipe.container as string).first();
    const containerElement = container.get(0);
    if (containerElement == null) {
      return {
        ok: false,
        report: [`the container selector "${recipe.container}" matches nothing in the article`],
      };
    }
    const output = (recipe.extract as RecipeModule["extract"])($, toMarkdown);
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
      containerPath: pathOf(containerElement as Element),
      ignores: recipe.ignores ?? [],
      inventory: recipe.inventory ?? [],
    };
    return { ok: true, extraction };
  } catch (error) {
    return { ok: false, report: [`the recipe crashed: ${describeError(error)}`] };
  }
}
