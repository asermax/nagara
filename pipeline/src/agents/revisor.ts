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
  // Flue defaults the thinking level to "medium"; asking for none is what routes
  // the request through the model entry's "off" mapping, the cheapest effort this
  // endpoint accepts. Thinking cannot be disabled outright here.
  useModel(env.agentModel, { thinkingLevel: "off" });
  const { html } = useInitialData<v.InferOutput<typeof RevisorInitialData>>();
  useExtractTool(html);
  return revisorInstruction(env.agentMaxTurns, html);
}

Revisor.initialData = RevisorInitialData;
Revisor.durability = AGENT_DURABILITY;
