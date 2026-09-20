"use agent";

import { env } from "cloudflare:workers";
import { useInitialData, useModel, useTool } from "@flue/runtime";
import * as v from "valibot";
import { runRecipe } from "../runtime/run.ts";
import { revisorInstruction } from "./prompts.ts";

export const RevisorInitialData = v.object({
  html: v.string(),
  recipe: v.string(),
});

export function Revisor() {
  useModel(env.agentModel);
  const { html } = useInitialData<v.InferOutput<typeof RevisorInitialData>>();
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
  return revisorInstruction(env.agentMaxTurns);
}

Revisor.initialData = RevisorInitialData;
Revisor.durability = { maxAttempts: 5, timeoutMs: 1_800_000 };
