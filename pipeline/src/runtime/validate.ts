import { load as loadCheerio } from "cheerio/slim";
import type { AnyNode, Element } from "domhandler";
import {
  comparePaths,
  type ElementPath,
  isPathInside,
  pathOf,
  resolvePath,
  samePath,
} from "./paths.ts";
import type { SerializedExtraction } from "./recipe.ts";

const UNREADABLE_TAGS = new Set(["script", "style", "noscript", "template", "head"]);

function describeElement($: ReturnType<typeof loadCheerio>, element: Element): string {
  const classes = $(element).attr("class");
  return classes ? `<${element.name} class="${classes}">` : `<${element.name}>`;
}

function checkGeometry(
  $: ReturnType<typeof loadCheerio>,
  extraction: SerializedExtraction,
  problems: string[],
): Element[] {
  const container = resolvePath($, extraction.containerPath);
  if (container == null) {
    problems.push("the recipe's container does not resolve against the article");
    return [];
  }
  const unitElements: Element[] = [];
  let previous: ElementPath | null = null;
  extraction.units.forEach((unit, position) => {
    const element = resolvePath($, unit.path);
    if (element == null) {
      problems.push(`unit ${position} does not resolve against the article`);
      return;
    }
    if (!isPathInside(unit.path, extraction.containerPath)) {
      problems.push(`unit ${position} sits outside the container`);
    }
    if (previous != null && comparePaths(unit.path, previous) <= 0) {
      problems.push(`unit ${position} is out of document order`);
    }
    for (const other of unitElements) {
      const otherPath = pathOf(other);
      if (isPathInside(unit.path, otherPath) || isPathInside(otherPath, unit.path)) {
        problems.push(`unit ${position} is nested inside another unit`);
        break;
      }
    }
    previous = unit.path;
    unitElements.push(element);
  });
  return unitElements;
}

function checkMarkdown(extraction: SerializedExtraction, problems: string[]): void {
  extraction.units.forEach((unit, position) => {
    if (unit.type === "image") {
      return;
    }
    if (unit.display.trim().length === 0) {
      problems.push(`unit ${position} carries empty markdown`);
      return;
    }
    const lines = unit.display.split("\n");
    const fences = lines.filter((line) => line.trimStart().startsWith("```")).length;
    if (fences % 2 !== 0) {
      problems.push(`unit ${position} has unbalanced code fences`);
    }
    const outsideCode = stripCode(unit.display);
    if (/<\/?(?![a-zA-Z]+:\/\/)[a-zA-Z][^<>]*>/.test(outsideCode)) {
      problems.push(`unit ${position} keeps residual HTML outside code blocks`);
    }
  });
}

function stripCode(markdown: string): string {
  return markdown.replace(/```[\s\S]*?```/g, "").replace(/`[^`\n]*`/g, "");
}

function checkLeftoverText(
  html: string,
  extraction: SerializedExtraction,
  problems: string[],
): void {
  const $ = loadCheerio(html);
  const container = resolvePath($, extraction.containerPath);
  if (container == null) {
    return;
  }
  // Resolve every path first, then remove: removing one element shifts the
  // positions of its later siblings, so a resolve interleaved with removal
  // would lose the units that follow.
  const removable: Element[] = [];
  for (const unit of extraction.units) {
    const element = resolvePath($, unit.path);
    if (element != null) {
      removable.push(element);
    }
  }
  for (const entry of extraction.inventory) {
    if (entry.role !== "title") {
      continue;
    }
    $(container)
      .find(entry.selector)
      .each((_index, node) => {
        removable.push(node as Element);
      });
  }
  for (const element of removable) {
    $(element).remove();
  }
  for (const ignore of extraction.ignores) {
    $(container).find(ignore.selector).remove();
  }
  const leftover = collectReadableText($, container);
  if (leftover.length > 0) {
    problems.push(`readable text is left after the units and ignores: ${leftover.join(" | ")}`);
  }
}

function collectReadableText($: ReturnType<typeof loadCheerio>, root: Element): string[] {
  const leftovers: string[] = [];
  $(root)
    .find("*")
    .each((_index, node) => {
      const element = node as Element;
      if (UNREADABLE_TAGS.has(element.name)) {
        return;
      }
      const own = $(element)
        .contents()
        .filter((_i, child: AnyNode) => child.type === "text")
        .text()
        .replace(/\s+/g, " ")
        .trim();
      if (own.length > 0) {
        leftovers.push(`${describeElement($, element)} “${own.slice(0, 120)}”`);
      }
    });
  return leftovers;
}

function checkInventory(
  $: ReturnType<typeof loadCheerio>,
  extraction: SerializedExtraction,
  unitElements: Element[],
  problems: string[],
): void {
  if (unitElements.length === 0 && extraction.inventory.length === 0) {
    return;
  }
  const container = resolvePath($, extraction.containerPath);
  if (container == null) {
    return;
  }
  const unitPaths = unitElements.map((element) => pathOf(element));
  const declared = new Set<Element>();
  for (const entry of extraction.inventory) {
    $(container)
      .find(entry.selector)
      .each((_index, node) => {
        declared.add(node as Element);
      });
  }
  const unexpected: string[] = [];
  $(container)
    .find("*")
    .each((_index, node) => {
      const element = node as Element;
      if (UNREADABLE_TAGS.has(element.name)) {
        return;
      }
      const path = pathOf(element);
      const insideUnit = unitPaths.some(
        (unitPath) => samePath(path, unitPath) || isPathInside(path, unitPath),
      );
      if (insideUnit || declared.has(element)) {
        return;
      }
      for (const ignore of extraction.ignores) {
        if ($(element).is(ignore.selector)) {
          return;
        }
      }
      unexpected.push(describeElement($, element));
    });
  if (unexpected.length > 0) {
    problems.push(
      `element kinds inside the container are neither units, ignored, nor declared in the inventory: ${unexpected.slice(0, 12).join(", ")}`,
    );
  }
}

export function validateExtraction(extraction: SerializedExtraction, html: string): string[] {
  const problems: string[] = [];
  const $ = loadCheerio(html);
  const unitElements = checkGeometry($, extraction, problems);
  checkMarkdown(extraction, problems);
  checkInventory($, extraction, unitElements, problems);
  checkLeftoverText(html, extraction, problems);
  return problems;
}
