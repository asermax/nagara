import { env } from "cloudflare:workers";
import { describe, expect, it } from "vitest";
import { executeInDynamicWorker, PlatformFailure, runRecipe } from "../src/runtime/run.ts";
import { articleHtml, passingRecipe } from "./fixtures/article.ts";

describe("runtime failure classification", () => {
  it("a recipe that throws against the article is a validation failure with its crash report", async () => {
    const throwing = passingRecipe.replace(
      "return { title, units };",
      "throw new Error('the markup moved');",
    );
    const result = await runRecipe(env, throwing, articleHtml);
    if (!result.ok) {
      expect(result.report.join("\n")).toMatch(/the recipe crashed.*the markup moved/);
    }
  });

  it("a recipe whose module does not parse is a validation failure", async () => {
    const result = await runRecipe(env, "export const container = ", articleHtml);
    if (!result.ok) {
      expect(result.report.join("\n")).toMatch(/recipe module does not load/);
    }
  });

  it("a recipe that is the reply envelope rather than a module is a validation failure", async () => {
    const envelope = JSON.stringify({ kind: "script", source: passingRecipe });
    const result = await runRecipe(env, envelope, articleHtml);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.report.join("\n")).toMatch(/recipe module does not load/);
    }
  });

  it("a dynamic worker whose bundle does not load is a platform failure", async () => {
    let failure: unknown;
    try {
      await executeInDynamicWorker(env, passingRecipe, articleHtml, {
        injectionSource: "throw new Error('the bundle did not load');",
      });
    } catch (error) {
      failure = error;
    }
    expect(failure).toBeInstanceOf(PlatformFailure);
    expect((failure as Error).message).toMatch(/unreachable/);
  });
});
