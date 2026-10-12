import { type AgentInitialData, type AgentKind, dispatchAgent, readAgent } from "./gateway.ts";

export type AgentConversation = (
  kind: AgentKind,
  conversationId: string,
  message: string,
  initialData: AgentInitialData,
) => Promise<string>;

export const agentConversation: AgentConversation = async (
  kind,
  conversationId,
  message,
  initialData,
) => {
  const receipt = await dispatchAgent(kind, conversationId, message, initialData);

  return (await readAgent(kind, conversationId, receipt)).text;
};
