import { env } from "cloudflare:workers";
import { describe, expect, it } from "vitest";
import { runRecipe } from "../src/runtime/run.ts";
import { articleHtml, passingRecipe } from "./fixtures/article.ts";

// The local half of the Dynamic Workers proof: workerd blocks every direct
// path to running source, so the whole runtime rides the Worker Loader. The
// real-edge half needs a personal-account `wrangler login` and runs manually.
describe("dynamic workers proof", () => {
  it("recipe source executes with the injection bundle and answers deterministically", async () => {
    const first = await runRecipe(env, passingRecipe, articleHtml);
    const second = await runRecipe(env, passingRecipe, articleHtml);
    expect(first).toEqual(second);
    expect(first.ok).toBe(true);
  });

  it.skip("the cpu limit kills a spinning recipe on the real edge", async () => {
    // miniflare's Worker Loader does not enforce `limits.cpuMs`, and a
    // synchronous spin freezes the local isolate outright, so the kill can
    // only be observed against the real platform. The recipe's death there
    // surfaces as a fetch failure in the extract call, which the runtime
    // classifies as a validation failure triggering revision.
    const spinning = passingRecipe.replace(
      "return { title, units };",
      "while (true) { units.push({ type: 'paragraph', display: 'x', element: $container.children().first().get(0) }); }",
    );
    const result = await runRecipe(env, spinning, articleHtml);
    expect(result.ok).toBe(false);
    expect(result.report?.join("\n")).toMatch(/recipe died during execution/);
  });
});
