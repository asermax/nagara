import { type CheerioAPI, load as loadCheerio } from "cheerio/slim";
import type { AnyNode, Element } from "domhandler";
import { comparePaths, type ElementPath, isPathInside, resolvePath } from "./paths.ts";
import type { SerializedExtraction } from "./recipe.ts";

const UNREADABLE_TAGS = new Set(["script", "style", "noscript", "template", "head"]);

interface ResolvedUnits {
  elements: Element[];
  problems: string[];
}

function describeElement($: CheerioAPI, element: Element): string {
  const classes = $(element).attr("class");
  return classes ? `<${element.name} class="${classes}">` : `<${element.name}>`;
}

function resolveUnits($: CheerioAPI, extraction: SerializedExtraction): ResolvedUnits {
  const resolved: ResolvedUnits = { elements: [], problems: [] };
  const paths: ElementPath[] = [];
  let previous: ElementPath | null = null;
  extraction.units.forEach((unit, position) => {
    const element = resolvePath($, unit.path);
    if (element == null) {
      resolved.problems.push(`unit ${position} does not resolve against the article`);
      return;
    }
    if (!isPathInside(unit.path, extraction.containerPath)) {
      resolved.problems.push(`unit ${position} sits outside the container`);
    }
    if (previous != null && comparePaths(unit.path, previous) <= 0) {
      resolved.problems.push(`unit ${position} is out of document order`);
    }
    for (const otherPath of paths) {
      if (isPathInside(unit.path, otherPath) || isPathInside(otherPath, unit.path)) {
        resolved.problems.push(`unit ${position} is nested inside another unit`);
        break;
      }
    }
    previous = unit.path;
    resolved.elements.push(element);
    paths.push(unit.path);
  });
  return resolved;
}

function collectReadableText($: CheerioAPI, root: Element): string[] {
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

function stripCode(markdown: string): string {
  return markdown.replace(/```[\s\S]*?```/g, "").replace(/`[^`\n]*`/g, "");
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

function ignoredElements(
  $: CheerioAPI,
  container: Element,
  extraction: SerializedExtraction,
): Set<Element> {
  const ignored = new Set<Element>();
  const combined = extraction.ignores.map((ignore) => ignore.selector).join(",");
  if (combined.length > 0) {
    $(container)
      .find(combined)
      .each((_index, node) => {
        ignored.add(node as Element);
      });
  }
  return ignored;
}

function checkInventory(
  $: CheerioAPI,
  extraction: SerializedExtraction,
  container: Element,
  resolved: ResolvedUnits,
  ignored: Set<Element>,
  problems: string[],
): void {
  if (extraction.inventory.length === 0) {
    return;
  }
  const covered = new Set<Element>(resolved.elements);
  for (const unitElement of resolved.elements) {
    $(unitElement)
      .find("*")
      .each((_index, node) => {
        covered.add(node as Element);
      });
  }
  for (const entry of extraction.inventory) {
    $(container)
      .find(entry.selector)
      .each((_index, node) => {
        covered.add(node as Element);
      });
  }
  const unexpected: string[] = [];
  $(container)
    .find("*")
    .each((_index, node) => {
      const element = node as Element;
      if (UNREADABLE_TAGS.has(element.name) || covered.has(element) || ignored.has(element)) {
        return;
      }
      unexpected.push(describeElement($, element));
    });
  if (unexpected.length > 0) {
    problems.push(
      `element kinds inside the container are neither units, ignored, nor declared in the inventory: ${unexpected.slice(0, 12).join(", ")}`,
    );
  }
}

function checkLeftoverText(
  $: CheerioAPI,
  extraction: SerializedExtraction,
  container: Element,
  resolved: ResolvedUnits,
  ignored: Set<Element>,
  problems: string[],
): void {
  // Runs last and owns the tree: it removes the units, the ignores and the
  // title-roled elements, and nothing after it reads the document.
  const removable: Element[] = [...resolved.elements];
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
  for (const element of ignored) {
    $(element).remove();
  }
  const leftover = collectReadableText($, container);
  if (leftover.length > 0) {
    problems.push(`readable text is left after the units and ignores: ${leftover.join(" | ")}`);
  }
}

export function validateExtraction(extraction: SerializedExtraction, html: string): string[] {
  const problems: string[] = [];
  const $ = loadCheerio(html);
  const container = resolvePath($, extraction.containerPath);
  if (container == null) {
    return ["the recipe's container does not resolve against the article"];
  }
  const resolved = resolveUnits($, extraction);
  const ignored = ignoredElements($, container, extraction);
  problems.push(...resolved.problems);
  checkMarkdown(extraction, problems);
  checkInventory($, extraction, container, resolved, ignored, problems);
  checkLeftoverText($, extraction, container, resolved, ignored, problems);
  return problems;
}
