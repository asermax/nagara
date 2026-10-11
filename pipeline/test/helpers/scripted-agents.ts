import type { AgentConversation } from "../../src/agents/conversation.ts";
import type { AgentKind } from "../../src/agents/gateway.ts";

export type ScriptedAgentReplies = Partial<Record<AgentKind, string>>;

const GAVE_UP =
  '```json\n{"kind": "gave-up", "reason": "no reply was scripted for this test"}\n```';

// The Workflow runs in the test file's isolate, so a global set by the test is what the stand-in
// reads when the recipe step asks an agent.
const REPLIES = Symbol.for("nagara.test.scripted-agent-replies");

const store = globalThis as { [REPLIES]?: ScriptedAgentReplies };

export const scriptAgents = (replies: ScriptedAgentReplies) => {
  store[REPLIES] = replies;
};

export const resetAgents = () => {
  delete store[REPLIES];
};

// Stands in for src/agents/conversation.ts under vitest: the pool never builds the Flue agents'
// Durable Objects, so every conversation answers with the reply the test scripted.
export const agentConversation: AgentConversation = async (kind) =>
  store[REPLIES]?.[kind] ?? GAVE_UP;
