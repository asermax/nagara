"use agent";

import { env } from "cloudflare:workers";
import { useInitialData, useModel } from "@flue/runtime";
import * as v from "valibot";
import { AGENT_DURABILITY, useExtractTool } from "./extract-tool.ts";
import { revisorInstruction } from "./prompts.ts";

export const RevisorInitialData = v.object({
  html: v.string(),
  recipe: v.string(),
});

export function Revisor() {
  useModel(env.agentModel);
  const { html } = useInitialData<v.InferOutput<typeof RevisorInitialData>>();
  useExtractTool(html);
  return revisorInstruction(env.agentMaxTurns);
}

Revisor.initialData = RevisorInitialData;
Revisor.durability = AGENT_DURABILITY;
