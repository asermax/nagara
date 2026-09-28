import type { CheerioAPI } from "cheerio/slim";
import { type AnyNode, type Element, isTag } from "domhandler";
import type { Unit } from "../units.ts";
import { toMarkdown } from "./markdown.ts";

const IMAGE_WRAPPERS = ["figure", "picture"];
const BLOCK_TAGS = ["pre", "img", "svg", ...IMAGE_WRAPPERS];

type Piece = { kind: "content"; node: AnyNode } | { kind: "block"; unit: Unit };

// A <figure> is only an image when it carries one: a <figure> wrapping a
// highlighted listing holds a <pre>, which has to surface as code instead.
function isBlock($: CheerioAPI, element: Element): boolean {
  if (element.name === "figure") {
    return $(element).find("img").length > 0;
  }
  return BLOCK_TAGS.includes(element.name);
}

// Every element between the list and a block, found in one pass so the
// recursion never rescans a subtree to learn whether it has to split.
function blockHolders($: CheerioAPI, list: Element): Set<Element> {
  const holders = new Set<Element>();

  for (const block of $(list).find(BLOCK_TAGS.join(", ")).toArray()) {
    if (!isBlock($, block)) {
      continue;
    }

    holders.add(list);
    for (const ancestor of $(block).parentsUntil(list).toArray()) {
      holders.add(ancestor);
    }
  }

  return holders;
}

function blockUnit($: CheerioAPI, block: Element): Unit {
  if (block.name === "pre") {
    return { type: "code", display: toMarkdown(block) };
  }

  const $image = IMAGE_WRAPPERS.includes(block.name) ? $(block).find("img").first() : $(block);
  const alt = $image.attr("alt") ?? "";
  return { type: "image", display: alt, src: $image.attr("src") ?? "", alt };
}

// Whitespace left between tags once a nested list or a block is pulled out of
// an item carries nothing; wrapping it would open a spurious empty item.
function isMeaningful(node: AnyNode): boolean {
  if (node.type === "text") {
    return node.data.trim().length > 0;
  }
  return isTag(node);
}

function splitNode($: CheerioAPI, holders: Set<Element>, node: AnyNode): Piece[] {
  if (isTag(node) && isBlock($, node)) {
    return [{ kind: "block", unit: blockUnit($, node) }];
  }

  if (isTag(node) && holders.has(node)) {
    return splitAround($, holders, node);
  }

  return [{ kind: "content", node: $(node).clone().get(0) as AnyNode }];
}

// Every run of content between two blocks goes back into a copy of the
// element it came from, so an item resumed after a block reopens as an empty
// <li> at each level above it, and an ordered part starts at the number of
// the first item it carries.
function splitAround($: CheerioAPI, holders: Set<Element>, element: Element): Piece[] {
  const pieces: Piece[] = [];
  let run: AnyNode[] = [];
  let runStart: number | null = null;

  const flush = () => {
    if (run.some(isMeaningful)) {
      const part = $(element).clone().empty();
      part.append(run);

      if (element.name === "ol" && runStart != null) {
        part.attr("start", String(runStart));
      }

      pieces.push({ kind: "content", node: part.get(0) as AnyNode });
    }

    run = [];
    runStart = null;
  };

  let number = Number.parseInt($(element).attr("start") ?? "1", 10);
  for (const child of element.children) {
    const isItem = isTag(child) && child.name === "li";
    const childNumber = number;
    if (isItem) {
      number += 1;
    }

    for (const piece of splitNode($, holders, child)) {
      if (piece.kind === "block") {
        flush();
        pieces.push(piece);
        continue;
      }

      if (isItem && runStart == null) {
        runStart = childNumber;
      }
      run.push(piece.node);
    }
  }
  flush();

  return pieces;
}

export function splitList($: CheerioAPI, list: Element): Unit[] | null {
  const holders = blockHolders($, list);
  if (holders.size === 0) {
    return null;
  }

  return splitAround($, holders, list).map((piece) =>
    piece.kind === "block" ? piece.unit : { type: "paragraph", display: toMarkdown(piece.node) },
  );
}
