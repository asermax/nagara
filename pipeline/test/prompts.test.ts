import { describe, expect, it } from "vitest";
import { authorInstruction, RECIPE_CONTRACT, revisorInstruction } from "../src/agents/prompts.ts";
import { articleHtml } from "./fixtures/article.ts";

describe("the article embedded in an agent's instruction", () => {
  it("carries the article's html so the agent reads the page before its first call", () => {
    expect(authorInstruction(100, articleHtml)).toContain(articleHtml);
    expect(revisorInstruction(100, articleHtml)).toContain(articleHtml);
  });
});

describe("the recipe rules an agent's instruction carries", () => {
  const rules = [
    "to GFM markdown with the fixed converter",
    "Pass it the whole element, never its children or a piece of it.",
    "A list (ol or ul) is one unit, never one unit per li, even when it holds code blocks or images.",
    "Every <math> element is a formula, wherever it sits: inline inside a paragraph, a list item, a table cell or a quote, as well as a block formula. Replace each one in the clone with its alttext as plain text, with no delimiter around it, before calling toMarkdown.",
    "a blockquote's attribution (its footer or cite), a dl, footnote markers and the footnote list, a heading's self-link (the heading's own text stays), and any heading that repeats the article's title",
    "Keep a task list's checkboxes.",
  ];

  it("the author instruction carries every markdown rule of the recipe contract", () => {
    const instruction = authorInstruction(100, articleHtml);

    for (const rule of rules) {
      expect(instruction).toContain(rule);
    }
  });

  it("the revision instruction carries the same rule text as the author instruction", () => {
    expect(revisorInstruction(100, articleHtml)).toContain(RECIPE_CONTRACT);
    expect(authorInstruction(100, articleHtml)).toContain(RECIPE_CONTRACT);
  });
});
