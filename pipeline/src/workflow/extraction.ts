import { WorkflowEntrypoint, type WorkflowEvent, type WorkflowStep } from "cloudflare:workers";
import { authorMessage, revisionMessage } from "../agents/prompts.ts";
import { parseSettlement, type Settlement } from "../agents/settlement.ts";
import { describeError } from "../errors.ts";
import type { JobStatusBody } from "../http/job-status.ts";
import { domainQueueStub } from "../queue/domain-queue.ts";
import type { Unit } from "../runtime/units.ts";
import { resolveWorld, type WorkflowWorld } from "./world.ts";

export interface ExtractionParams {
  html: string;
  recipe?: string;
  domain: string;
}

type GuardedRun =
  | { outcome: "ok"; title: string; units: Unit[] }
  | { outcome: "invalid"; report: string[] }
  | { outcome: "platform"; failure: string };

async function guardedRun(world: WorkflowWorld, source: string, html: string): Promise<GuardedRun> {
  try {
    const result = await world.runRecipe(source, html);
    if (result.ok) {
      return { outcome: "ok", title: result.title ?? "", units: result.units ?? [] };
    }
    return { outcome: "invalid", report: result.report ?? ["the run failed without a report"] };
  } catch (error) {
    return { outcome: "platform", failure: describeError(error) };
  }
}

interface AttemptOptions {
  kind: "author" | "revision";
  retries: number;
  jobId: string;
  html: string;
  recipe?: string;
  label: string;
  message: (report: string[] | null) => string;
  exhausted: string;
  seedReport?: string[];
}

// One bounded loop for both prompts: every attempt is a fresh conversation
// (the bare job id first, suffixed ids after), the settled script is re-run
// through the runtime, and the failing report feeds the next attempt's
// message.
async function settleRecipe(
  world: WorkflowWorld,
  step: WorkflowStep,
  options: AttemptOptions,
): Promise<JobStatusBody> {
  let report: string[] | null = options.seedReport ?? null;
  for (let attempt = 1; attempt <= 1 + options.retries; attempt += 1) {
    const conversationId = attempt === 1 ? options.jobId : `${options.jobId}-${attempt}`;
    const receipt = await step.do(`${options.label} attempt ${attempt}: dispatch`, () =>
      world.dispatchAgent(options.kind, conversationId, options.message(report), {
        html: options.html,
        recipe: options.recipe,
      }),
    );
    const settlement: Settlement = await step.do(
      `${options.label} attempt ${attempt}: read`,
      async () => {
        try {
          const reply = await world.readAgent(options.kind, conversationId, receipt);
          return parseSettlement(reply.text);
        } catch (error) {
          return { kind: "gave-up", reason: describeError(error) };
        }
      },
    );
    if (settlement.kind === "not-article") {
      return { state: "not_article" };
    }
    if (settlement.kind === "script") {
      const run = await step.do(`${options.label} attempt ${attempt}: run script`, () =>
        guardedRun(world, settlement.source, options.html),
      );
      if (run.outcome === "platform") {
        return { state: "error", error: run.failure };
      }
      if (run.outcome === "ok") {
        return {
          state: "complete",
          title: run.title,
          units: run.units,
          recipe: settlement.source,
        };
      }
      report = run.report;
    }
  }
  return { state: "error", error: options.exhausted };
}

export class ExtractionWorkflow extends WorkflowEntrypoint<Cloudflare.Env, ExtractionParams> {
  async run(event: WorkflowEvent<ExtractionParams>, step: WorkflowStep): Promise<JobStatusBody> {
    const { html, recipe, domain } = event.payload;
    const jobId = event.instanceId;
    const world = resolveWorld(this.env);

    let terminal: JobStatusBody;
    if (recipe != null) {
      const first = await step.do("run provided recipe", () => guardedRun(world, recipe, html));
      if (first.outcome === "platform") {
        terminal = { state: "error", error: first.failure };
      } else if (first.outcome === "ok") {
        terminal = { state: "complete", title: first.title, units: first.units };
      } else {
        terminal = await settleRecipe(world, step, {
          kind: "revision",
          retries: this.env.revisionRetries,
          jobId,
          html,
          recipe,
          label: "revision",
          message: (report) => revisionMessage(domain, report ?? [], recipe),
          exhausted:
            "revision gave up: the recipe still fails the article and the old version stands",
          seedReport: first.report,
        });
      }
    } else {
      terminal = await settleRecipe(world, step, {
        kind: "author",
        retries: this.env.authoringRetries,
        jobId,
        html,
        label: "authoring",
        message: (report) => authorMessage(domain, report),
        exhausted: "authoring gave up: nothing is saved for the domain and the item fails",
      });
    }

    await step.do("release lease", async () => {
      try {
        await domainQueueStub(this.env, domain).release(jobId);
        return { released: true };
      } catch (error) {
        return { released: false, error: describeError(error) };
      }
    });

    return terminal;
  }
}
