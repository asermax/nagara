import { WorkflowEntrypoint, type WorkflowEvent, type WorkflowStep } from "cloudflare:workers";
import { authorMessage, revisionMessage } from "../agents/prompts.ts";
import { parseSettlement, type Settlement } from "../agents/settlement.ts";
import type { JobStatusBody } from "../http/job-status.ts";
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

function describeError(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return String(error);
}

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

async function dispatchAndRead(
  world: WorkflowWorld,
  step: WorkflowStep,
  options: {
    kind: "author" | "revision";
    conversationId: string;
    message: string;
    initialData: { html: string; recipe?: string };
    label: string;
  },
): Promise<Settlement> {
  const receipt = await step.do(`${options.label}: dispatch`, () =>
    world.dispatchAgent(options.kind, options.conversationId, options.message, options.initialData),
  );
  return await step.do(`${options.label}: read`, async () => {
    try {
      const reply = await world.readAgent(options.kind, options.conversationId, receipt);
      return parseSettlement(reply.text);
    } catch (error) {
      return { kind: "gave-up", reason: describeError(error) };
    }
  });
}

function complete(title: string, units: Unit[], source?: string): JobStatusBody {
  return source == null
    ? { state: "complete", title, units }
    : { state: "complete", title, units, recipe: source };
}

export class ExtractionWorkflow extends WorkflowEntrypoint<Cloudflare.Env, ExtractionParams> {
  async run(event: WorkflowEvent<ExtractionParams>, step: WorkflowStep): Promise<JobStatusBody> {
    const { html, recipe, domain } = event.payload;
    const jobId = event.instanceId;
    const world = resolveWorld(this.env);
    const { authoringRetries, revisionRetries } = this.env;

    const terminal =
      recipe != null
        ? await this.runWithRevision(world, step, { html, recipe, domain, jobId, revisionRetries })
        : await this.runWithAuthoring(world, step, { html, domain, jobId, authoringRetries });

    await step.do("release lease", async () => {
      try {
        const id = this.env.DOMAIN_QUEUE.idFromName(domain);
        await this.env.DOMAIN_QUEUE.get(id).fetch("https://queue/release", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ job_id: jobId }),
        });
        return { released: true };
      } catch (error) {
        return { released: false, error: describeError(error) };
      }
    });

    return terminal;
  }

  private async runWithRevision(
    world: WorkflowWorld,
    step: WorkflowStep,
    input: {
      html: string;
      recipe: string;
      domain: string;
      jobId: string;
      revisionRetries: number;
    },
  ): Promise<JobStatusBody> {
    const first = await step.do("run provided recipe", () =>
      guardedRun(world, input.recipe, input.html),
    );
    if (first.outcome === "platform") {
      return { state: "error", error: first.failure };
    }
    if (first.outcome === "ok") {
      return complete(first.title, first.units);
    }
    let report = first.report;
    for (let attempt = 1; attempt <= 1 + input.revisionRetries; attempt += 1) {
      const conversationId = attempt === 1 ? input.jobId : `${input.jobId}-${attempt}`;
      const settlement = await dispatchAndRead(world, step, {
        kind: "revision",
        conversationId,
        message: revisionMessage(input.domain, report, input.html, input.recipe),
        initialData: { html: input.html, recipe: input.recipe },
        label: `revision attempt ${attempt}`,
      });
      if (settlement.kind === "not-article") {
        return { state: "not_article" };
      }
      if (settlement.kind === "script") {
        const run = await step.do(`revision attempt ${attempt}: run script`, () =>
          guardedRun(world, settlement.source, input.html),
        );
        if (run.outcome === "platform") {
          return { state: "error", error: run.failure };
        }
        if (run.outcome === "ok") {
          return complete(run.title, run.units, settlement.source);
        }
        report = run.outcome === "invalid" ? run.report : [];
      }
    }
    return {
      state: "error",
      error: "revision gave up: the recipe still fails the article and the old version stands",
    };
  }

  private async runWithAuthoring(
    world: WorkflowWorld,
    step: WorkflowStep,
    input: {
      html: string;
      domain: string;
      jobId: string;
      authoringRetries: number;
    },
  ): Promise<JobStatusBody> {
    for (let attempt = 1; attempt <= 1 + input.authoringRetries; attempt += 1) {
      const conversationId = attempt === 1 ? input.jobId : `${input.jobId}-${attempt}`;
      const settlement = await dispatchAndRead(world, step, {
        kind: "author",
        conversationId,
        message: authorMessage(input.domain, input.html),
        initialData: { html: input.html },
        label: `authoring attempt ${attempt}`,
      });
      if (settlement.kind === "not-article") {
        return { state: "not_article" };
      }
      if (settlement.kind === "script") {
        const run = await step.do(`authoring attempt ${attempt}: run script`, () =>
          guardedRun(world, settlement.source, input.html),
        );
        if (run.outcome === "platform") {
          return { state: "error", error: run.failure };
        }
        if (run.outcome === "ok") {
          return complete(run.title, run.units, settlement.source);
        }
      }
    }
    return {
      state: "error",
      error: "authoring gave up: nothing is saved for the domain and the item fails",
    };
  }
}
