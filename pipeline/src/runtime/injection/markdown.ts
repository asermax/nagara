import type { DominoDocument } from "@mixmark-io/domino";
import * as domino from "@mixmark-io/domino";
import { gfm } from "@truto/turndown-plugin-gfm";
import { load as loadCheerio } from "cheerio/slim";
import TurndownService from "turndown";

const turndown = new TurndownService({
  codeBlockStyle: "fenced",
  headingStyle: "atx",
  hr: "---",
  bulletListMarker: "-",
});
turndown.use(gfm);

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

const $render = loadCheerio("");

// Turndown fences a <pre> only when its first child is a <code>; anything
// else inside a <pre> would come out as a plain paragraph.
function wrapBarePre(document: DominoDocument): void {
  for (const pre of Array.from(document.body.querySelectorAll("pre"))) {
    if (pre.firstChild?.nodeName === "CODE") {
      continue;
    }

    const code = document.createElement("code");
    while (pre.firstChild != null) {
      code.appendChild(pre.firstChild);
    }
    pre.appendChild(code);
  }
}

export function toMarkdown(element: unknown): string {
  const document = domino.createDocument(`<body>${$render.html(element as never)}</body>`);
  wrapBarePre(document);
  return turndown.turndown(document.body).trim();
}
