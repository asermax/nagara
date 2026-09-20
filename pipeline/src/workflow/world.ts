import {
  type AgentDispatchReceipt,
  type AgentInitialData,
  type AgentKind,
  dispatchAgent,
  readAgent,
} from "../agents/gateway.ts";
import type { RecipeRun } from "../runtime/recipe.ts";
import { runRecipe } from "../runtime/run.ts";

export interface WorkflowWorld {
  runRecipe(source: string, html: string): Promise<RecipeRun>;
  dispatchAgent(
    kind: AgentKind,
    conversationId: string,
    message: string,
    initialData: AgentInitialData,
  ): Promise<AgentDispatchReceipt>;
  readAgent(
    kind: AgentKind,
    conversationId: string,
    receipt: AgentDispatchReceipt,
  ): Promise<{ text: string }>;
}

export const WORLD_SEAM = Symbol.for("nagara.workflow.world");

export function resolveWorld(env: Cloudflare.Env): WorkflowWorld {
  const override = (globalThis as Record<symbol, WorkflowWorld | undefined>)[WORLD_SEAM];
  if (override != null) {
    return override;
  }
  return {
    runRecipe: (source, html) => runRecipe(env, source, html),
    dispatchAgent: (kind, conversationId, message, initialData) =>
      dispatchAgent(kind, conversationId, message, initialData),
    readAgent: (kind, conversationId, receipt) => readAgent(kind, conversationId, receipt),
  };
}
