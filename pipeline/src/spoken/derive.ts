import MarkdownIt, { type Token } from "markdown-it";
import { sanitizeSpoken } from "./sanitize.ts";

type Node = {
  type: string;
  token: Token | null;
  children: Node[];
};

export const CODE_PLACEHOLDER = "Code sample.";

const FENCE = /^[ ]{0,3}(```|~~~)/;

const TASK_BOX = /^\[[ xX]\]\s+/;

const markdown = new MarkdownIt("commonmark").enable(["table", "strikethrough"]);

// markdown-it hands back a flat token stream; nesting it by the open and close tokens gives the
// block tree the walk below reads.
const toTree = (tokens: Token[]) => {
  const root: Node = { type: "root", token: null, children: [] };
  const stack = [root];

  for (const token of tokens) {
    const parent = stack[stack.length - 1];

    if (token.nesting === 1) {
      const node: Node = { type: token.type.replace(/_open$/, ""), token, children: [] };

      parent.children.push(node);
      stack.push(node);
    } else if (token.nesting === -1) {
      stack.pop();
    } else {
      parent.children.push({ type: token.type, token, children: [] });
    }
  }

  return root;
};

const inlineText = (inline: Token) =>
  (inline.children ?? [])
    .map((child) => {
      if (child.type === "text" || child.type === "code_inline") {
        return child.content;
      }

      return child.type === "softbreak" || child.type === "hardbreak" ? " " : "";
    })
    .join("");

const asSentence = (line: string) => (/[.!?]$/.test(line.trimEnd()) ? line : `${line}.`);

// A table reads as one header-aware line per body row ("Col: value, Col: value.") instead of
// speaking pipe characters; a table with no body rows reads its header cells.
const tableLines = (table: Node) => {
  const [header, ...body] = table.children.flatMap((section) =>
    section.children.map((row) => row.children.map((cell) => blockLines(cell).join(""))),
  );

  if (body.length === 0) {
    return [asSentence(header.join(", "))];
  }

  return body.map((row) =>
    asSentence(row.map((cell, index) => `${header[index]}: ${cell}`).join(", ")),
  );
};

// An item's marker and checkbox go on its own first paragraph. An item with no text of its own
// (one that opens with a nested list, or holds only an image or a code block) gets no line rather
// than a bare number, and its nested items keep their own numbering.
const itemLines = (item: Node, marker: string) => {
  const lines = item.children.flatMap(blockLines);

  if (item.children[0]?.type === "paragraph" && lines[0].trim() !== "") {
    lines[0] = marker + lines[0].replace(TASK_BOX, "");
  }

  return lines;
};

const blockLines = (node: Node): string[] => {
  if (node.type === "inline" && node.token != null) {
    return [inlineText(node.token)];
  }

  if (node.type === "table") {
    return tableLines(node);
  }

  if (node.type === "ordered_list") {
    const start = Number(node.token?.attrGet("start") ?? 1);

    return node.children.flatMap((item, index) => itemLines(item, `${start + index}. `));
  }

  if (node.type === "bullet_list") {
    return node.children.flatMap((item) => itemLines(item, ""));
  }

  return node.children.flatMap(blockLines);
};

// One line per block: emphasis and strikethrough read as their words, a link as its anchor text, a
// heading or quote without its marker, a code block or an image nested in a list is silent.
// Run-in emphasis that fails CommonMark's flanking rule (`review.**Agents`) is left as literal
// markers by the parser, so the sanitize tail still has markers to clear.
export const toSpoken = (display: string) => {
  if (FENCE.test(display)) {
    return CODE_PLACEHOLDER;
  }

  return sanitizeSpoken(blockLines(toTree(markdown.parse(display, {}))).join("\n"));
};
