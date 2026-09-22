"use agent";

import { env } from "cloudflare:workers";
import { useInitialData, useModel } from "@flue/runtime";
import * as v from "valibot";
import { AGENT_DURABILITY, useExtractTool } from "./extract-tool.ts";
import { authorInstruction } from "./prompts.ts";

export const AuthorInitialData = v.object({
  html: v.string(),
});

export function Author() {
  // Flue defaults the thinking level to "medium"; asking for none is what routes
  // the request through the model entry's "off" mapping, the cheapest effort this
  // endpoint accepts. Thinking cannot be disabled outright here.
  useModel(env.agentModel, { thinkingLevel: "off" });
  const { html } = useInitialData<v.InferOutput<typeof AuthorInitialData>>();
  useExtractTool(html);
  return authorInstruction(env.agentMaxTurns, html);
}

Author.initialData = AuthorInitialData;
Author.durability = AGENT_DURABILITY;
