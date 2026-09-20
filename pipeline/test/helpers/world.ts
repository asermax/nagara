import { env } from "cloudflare:workers";
import type { AgentDispatchReceipt } from "../../src/agents/gateway.ts";
import { scriptReply } from "../../src/agents/settlement.ts";
import type { RecipeRun } from "../../src/runtime/recipe.ts";
import { runRecipe } from "../../src/runtime/run.ts";
import { WORLD_SEAM, type WorkflowWorld } from "../../src/workflow/world.ts";

export function installWorld(world: WorkflowWorld): void {
  (globalThis as Record<symbol, WorkflowWorld>)[WORLD_SEAM] = world;
}

export function clearWorld(): void {
  delete (globalThis as Record<symbol, WorkflowWorld>)[WORLD_SEAM];
}

export const NOT_ARTICLE_REPLY = '```json\n{"kind": "not-article"}\n```';
export const GAVE_UP_REPLY = '```json\n{"kind": "gave-up", "reason": "the double gives up"}\n```';

export interface DoubleOptions {
  author?: string | (() => string);
  revision?: string | (() => string);
  runRecipe?: (source: string, html: string) => Promise<RecipeRun>;
  onAuthorDispatch?: () => void;
  onRevisionDispatch?: () => void;
}

export function worldWithAgents(options: DoubleOptions): WorkflowWorld {
  const asText = (value: string | (() => string) | undefined) => () =>
    typeof value === "function" ? value() : (value ?? GAVE_UP_REPLY);
  const authorReply = asText(options.author);
  const revisionReply = asText(options.revision);
  const run = options.runRecipe ?? ((source, html) => runRecipe(env, source, html));
  return {
    async runRecipe(source, html) {
      return await run(source, html);
    },
    async dispatchAgent(kind, conversationId) {
      if (kind === "author") {
        options.onAuthorDispatch?.();
      } else {
        options.onRevisionDispatch?.();
      }
      const agentReceipt: AgentDispatchReceipt = {
        submissionId: `sub-${conversationId}`,
        acceptedAt: "2026-09-19T00:00:00.000Z",
        uid: `uid-${conversationId}`,
      };
      return agentReceipt;
    },
    async readAgent(kind) {
      return { text: kind === "author" ? authorReply() : revisionReply() };
    },
  };
}

export function slowRunWorld(ms: number, options: DoubleOptions = {}): WorkflowWorld {
  const inner = worldWithAgents(options);
  return {
    ...inner,
    async runRecipe(source, html) {
      await new Promise((resolve) => setTimeout(resolve, ms));
      return await inner.runRecipe(source, html);
    },
  };
}

export function scriptReplyText(source: string): string {
  return scriptReply(source);
}
