import { env } from "cloudflare:workers";
import { describe, expect, it } from "vitest";
import { runRecipe } from "../src/runtime/run.ts";
import { articleHtml, failingRecipe, passingRecipe } from "./fixtures/article.ts";

describe("runtime smoke", () => {
  it("runs a real recipe in the dynamic worker and validates it", async () => {
    const result = await runRecipe(env, passingRecipe, articleHtml);
    if (!result.ok) {
      throw new Error(JSON.stringify(result.report));
    }
    expect(result.title).toBe("Colorless Green Ideas");
    expect(result.units.length).toBe(5);
    expect(result.units[0]).toEqual({
      type: "paragraph",
      display: "Noam _Chomsky_ coined the sentence to show that syntax can outrun sense.",
    });
    expect(result.units?.[1]).toEqual({
      type: "code",
      display: "`const ideas = colorless();`",
    });
    expect(result.units?.[2]).toEqual({
      type: "image",
      display: "A green idea, colorless",
      src: "/img/ideas.png",
      alt: "A green idea, colorless",
    });
    expect(result.units?.[3]).toEqual({
      type: "paragraph",
      display: "The famous sentence.",
    });
    expect(result.units[4].display).toBe("Second paragraph with a [link](https://example.com).");
  });

  it("fails validation when the recipe skips article content", async () => {
    const result = await runRecipe(env, failingRecipe, articleHtml);
    if (!result.ok) {
      expect(result.report.join("\n")).toMatch(/readable text is left/);
    }
  });
});
