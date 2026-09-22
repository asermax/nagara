import { describe, expect, it } from "vitest";
import { authorInstruction, revisorInstruction } from "../src/agents/prompts.ts";
import { articleHtml } from "./fixtures/article.ts";

describe("the article embedded in an agent's instruction", () => {
  it("carries the article's html so the agent reads the page before its first call", () => {
    expect(authorInstruction(100, articleHtml)).toContain(articleHtml);
    expect(revisorInstruction(100, articleHtml)).toContain(articleHtml);
  });
});
