import { init } from "@flue/runtime";
import type * as v from "valibot";
import { Author, type AuthorInitialData } from "./author.ts";
import { Revisor, type RevisorInitialData } from "./revisor.ts";

export type AgentKind = "author" | "revision";

export interface AgentDispatchReceipt {
  submissionId: string;
  acceptedAt: string;
  uid: string;
}

export interface AgentInitialData {
  html: string;
  recipe?: string;
}

function agentFor(kind: AgentKind) {
  return kind === "author" ? Author : Revisor;
}

function initialDataFor(kind: AgentKind, data: AgentInitialData): unknown {
  if (kind === "author") {
    return { html: data.html } satisfies v.InferOutput<typeof AuthorInitialData>;
  }
  return { html: data.html, recipe: data.recipe ?? "" } satisfies v.InferOutput<
    typeof RevisorInitialData
  >;
}

export async function dispatchAgent(
  kind: AgentKind,
  conversationId: string,
  message: string,
  initialData: AgentInitialData,
): Promise<AgentDispatchReceipt> {
  const handle = init(agentFor(kind), { id: conversationId });
  return await handle.dispatch({ message, initialData: initialDataFor(kind, initialData) });
}

export async function readAgent(
  kind: AgentKind,
  conversationId: string,
  receipt: AgentDispatchReceipt,
): Promise<{ text: string }> {
  const handle = init(agentFor(kind), { id: conversationId });
  const reply = await handle.read(receipt);
  return { text: reply.text };
}
