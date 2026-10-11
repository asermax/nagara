import { type AgentInitialData, type AgentKind, dispatchAgent, readAgent } from "./gateway.ts";

export type AgentConversation = {
  converse: (
    kind: AgentKind,
    conversationId: string,
    message: string,
    initialData: AgentInitialData,
  ) => Promise<string>;
};

export type ScriptedAgentReplies = Partial<Record<AgentKind, string>>;

const flue: AgentConversation = {
  converse: async (kind, conversationId, message, initialData) => {
    const receipt = await dispatchAgent(kind, conversationId, message, initialData);

    return (await readAgent(kind, conversationId, receipt)).text;
  },
};

const scripted = (replies: ScriptedAgentReplies): AgentConversation => ({
  converse: async (kind) => {
    const reply = replies[kind];

    if (reply == null) {
      throw new Error(`no scripted reply for the ${kind} agent`);
    }

    return reply;
  },
});

// A deployment that supplies scripted replies answers every agent conversation with them instead
// of reaching the Flue agents: the vitest pool never builds the agents' Durable Objects, so the
// Workflow's tests configure their replies here.
export const agentConversation = (env: Cloudflare.Env) =>
  env.scriptedAgentReplies == null
    ? flue
    : scripted(JSON.parse(env.scriptedAgentReplies) as ScriptedAgentReplies);
