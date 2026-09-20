import { env } from "cloudflare:workers";
import { useTool } from "@flue/runtime";
import * as v from "valibot";
import { runRecipe } from "../runtime/run.ts";

export const AGENT_DURABILITY = { maxAttempts: 5, timeoutMs: 1_800_000 };

export function useExtractTool(html: string): void {
  useTool({
    name: "extract",
    description:
      "Run a candidate recipe against the article and return its extraction result or its validation report.",
    input: v.object({ recipe: v.string() }),
    output: undefined,
    async run({ data }) {
      return { output: await runRecipe(env, data.recipe, html) };
    },
  });
}
