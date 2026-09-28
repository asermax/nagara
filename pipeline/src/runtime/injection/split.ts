import type { CheerioAPI } from "cheerio/slim";
import type { AnyNode, Element } from "domhandler";
import type { Unit } from "../units.ts";
import { toMarkdown } from "./markdown.ts";

const BLOCK_SELECTOR = "pre, img, figure, picture, svg";

type Piece = { kind: "content"; node: AnyNode } | { kind: "block"; unit: Unit };

function isElement(node: AnyNode): node is Element {
  return node.type === "tag" || node.type === "script" || node.type === "style";
}

// A <figure> is only an image when it carries one: a <figure> wrapping a
// highlighted listing holds a <pre>, which has to surface as code instead.
function isBlock($: CheerioAPI, element: Element): boolean {
  if (element.name === "figure") {
    return $(element).find("img").length > 0;
  }
  return ["pre", "img", "picture", "svg"].includes(element.name);
}

export function holdsBlock($: CheerioAPI, element: Element): boolean {
  return $(element).find(BLOCK_SELECTOR).length > 0;
}

function blockUnit($: CheerioAPI, block: Element): Unit {
  if (block.name === "pre") {
    return { type: "code", display: toMarkdown(block) };
  }

  const $image =
    block.name === "figure" || block.name === "picture" ? $(block).find("img").first() : $(block);
  const alt = $image.attr("alt") ?? "";
  return { type: "image", display: alt, src: $image.attr("src") ?? "", alt };
}

// Whitespace left between tags once a nested list or a block is pulled out of
// an item carries nothing; wrapping it would open a spurious empty item.
function isMeaningful(node: AnyNode): boolean {
  if (node.type === "text") {
    return node.data.trim().length > 0;
  }
  return isElement(node);
}

function splitNode($: CheerioAPI, node: AnyNode): Piece[] {
  if (!isElement(node)) {
    return [{ kind: "content", node: $(node).clone().get(0) as AnyNode }];
  }

  if (isBlock($, node)) {
    return [{ kind: "block", unit: blockUnit($, node) }];
  }

  if (!holdsBlock($, node)) {
    return [{ kind: "content", node: $(node).clone().get(0) as AnyNode }];
  }

  return splitAround($, node);
}

// Every run of content between two blocks goes back into a copy of the
// element it came from, so an item resumed after a block reopens as an empty
// <li> at each level above it, and an ordered part starts at the number of
// the first item it carries.
function splitAround($: CheerioAPI, element: Element): Piece[] {
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
    const isItem = isElement(child) && child.name === "li";
    const childNumber = number;
    if (isItem) {
      number += 1;
    }

    for (const piece of splitNode($, child)) {
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

export function splitList($: CheerioAPI, list: Element): Unit[] {
  return splitAround($, list).map((piece) =>
    piece.kind === "block" ? piece.unit : { type: "paragraph", display: toMarkdown(piece.node) },
  );
}
