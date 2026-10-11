import { agentConversation } from "../agents/conversation.ts";
import { authorMessage, revisionMessage } from "../agents/prompts.ts";
import { parseSettlement } from "../agents/settlement.ts";
import { runRecipe } from "../runtime/run.ts";
import type { Unit } from "../runtime/units.ts";

export type SettleRequest = {
  instanceId: string;
  domain: string;
  html: string;
  recipe: string | null;
};

export type Settled =
  | { kind: "ok"; title: string; units: Unit[]; script: string; isNew: boolean }
  | { kind: "not-article" }
  | { kind: "gave-up"; reason: string };

type Attempts = {
  agent: "author" | "revision";
  retries: number;
  message: (report: string[] | null) => string;
  report: string[] | null;
  exhausted: string;
};

// The conversation is keyed by the Workflow instance alone, so every attempt here, the recipe
// step's own retries and a restart from that step all continue one conversation. Every settled
// script runs through the runtime again: the reply never carries units.
const converge = async (
  env: Cloudflare.Env,
  { instanceId, html, recipe }: SettleRequest,
  attempts: Attempts,
): Promise<Settled> => {
  const conversation = agentConversation(env);
  let report = attempts.report;

  for (let attempt = 0; attempt <= attempts.retries; attempt += 1) {
    const reply = await conversation.converse(
      attempts.agent,
      instanceId,
      attempts.message(report),
      {
        html,
        recipe: recipe ?? undefined,
      },
    );
    const settlement = parseSettlement(reply);

    if (settlement.kind === "not-article") {
      return settlement;
    }

    if (settlement.kind === "script") {
      const run = await runRecipe(env, settlement.source, html);

      if (run.ok) {
        return {
          kind: "ok",
          title: run.title,
          units: run.units,
          script: settlement.source,
          isNew: true,
        };
      }

      report = run.report;
    }
  }

  return { kind: "gave-up", reason: attempts.exhausted };
};

export const settle = async (env: Cloudflare.Env, request: SettleRequest): Promise<Settled> => {
  const { domain, html, recipe } = request;

  if (recipe == null) {
    return converge(env, request, {
      agent: "author",
      retries: env.authoringRetries,
      message: (report) => authorMessage(domain, report),
      report: null,
      exhausted: "authoring gave up: nothing is saved for the domain",
    });
  }

  const run = await runRecipe(env, recipe, html);

  if (run.ok) {
    return { kind: "ok", title: run.title, units: run.units, script: recipe, isNew: false };
  }

  return converge(env, request, {
    agent: "revision",
    retries: env.revisionRetries,
    message: (report) => revisionMessage(domain, report ?? run.report, recipe),
    report: run.report,
    exhausted: "revision gave up: the recipe still fails the article and the old version stands",
  });
};
