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
  useModel(env.agentModel);
  const { html } = useInitialData<v.InferOutput<typeof AuthorInitialData>>();
  useExtractTool(html);
  return authorInstruction(env.agentMaxTurns);
}

Author.initialData = AuthorInitialData;
Author.durability = AGENT_DURABILITY;
