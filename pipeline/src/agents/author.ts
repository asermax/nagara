"use agent";

import { env } from "cloudflare:workers";
import { useInitialData, useModel, useTool } from "@flue/runtime";
import * as v from "valibot";
import { runRecipe } from "../runtime/run.ts";
import { authorInstruction } from "./prompts.ts";

export const AuthorInitialData = v.object({
  html: v.string(),
});

export function Author() {
  useModel(env.agentModel);
  const { html } = useInitialData<v.InferOutput<typeof AuthorInitialData>>();
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
  return authorInstruction(env.agentMaxTurns);
}

Author.initialData = AuthorInitialData;
Author.durability = { maxAttempts: 5, timeoutMs: 1_800_000 };
