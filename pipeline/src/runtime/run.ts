import { INJECTION_BUNDLE_SOURCE } from "../generated/injection-bundle.ts";
import { RUNTIME_MODULE } from "./glue.ts";
import type { ExecutionPayload, RecipeRun, SerializedExtraction } from "./recipe.ts";
import { toBoundaryUnit } from "./units.ts";
import { validateExtraction } from "./validate.ts";

const DYNAMIC_COMPAT_DATE = "2026-09-01";

export class PlatformFailure extends Error {
  constructor(message: string, cause?: unknown) {
    super(message);
    this.name = "PlatformFailure";
    this.cause = cause;
  }
}

function describeError(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return String(error);
}

export async function executeInDynamicWorker(
  env: Cloudflare.Env,
  recipeSource: string,
  html: string,
  options?: { injectionSource?: string },
): Promise<ExecutionPayload> {
  let worker: ReturnType<Cloudflare.Env["LOADER"]["load"]>;
  try {
    worker = env.LOADER.load({
      compatibilityDate: DYNAMIC_COMPAT_DATE,
      mainModule: "runtime.js",
      modules: {
        "runtime.js": { js: RUNTIME_MODULE },
        "injection.js": { js: options?.injectionSource ?? INJECTION_BUNDLE_SOURCE },
        "recipe.js": { js: recipeSource },
      },
      limits: { cpuMs: env.recipeCpuMs },
      globalOutbound: null,
    });
  } catch (error) {
    throw new PlatformFailure(`the recipe runtime did not load: ${describeError(error)}`, error);
  }

  // The health probe separates the two platform failures (an unreachable
  // dynamic worker, a bundle that does not load) from anything the recipe
  // itself does: the probe runs no recipe code, so its failure is the
  // platform's — unless the platform names the recipe module, which fails to
  // parse before any code runs and is the recipe's own fault.
  try {
    const probe = await worker.getEntrypoint().fetch(new Request("https://runtime/health"));
    if (!probe.ok) {
      throw new Error(`the health probe answered ${probe.status}`);
    }
  } catch (error) {
    if (/recipe\.js/.test(describeError(error))) {
      return { ok: false, report: [`the recipe module does not load: ${describeError(error)}`] };
    }
    throw new PlatformFailure(`the dynamic worker is unreachable: ${describeError(error)}`, error);
  }

  try {
    const response = await worker.getEntrypoint().fetch(
      new Request("https://runtime/extract", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ html }),
      }),
    );
    if (!response.ok) {
      throw new PlatformFailure(`the recipe runtime answered ${response.status}`);
    }
    return (await response.json()) as ExecutionPayload;
  } catch (error) {
    if (error instanceof PlatformFailure) {
      throw error;
    }
    return {
      ok: false,
      report: [`the recipe died during execution: ${describeError(error)}`],
    };
  }
}

export async function runRecipe(
  env: Cloudflare.Env,
  recipeSource: string,
  html: string,
): Promise<RecipeRun> {
  const execution = await executeInDynamicWorker(env, recipeSource, html);
  if (!execution.ok) {
    return { ok: false, report: execution.report };
  }
  const report = validateExtraction(execution.extraction, html);
  if (report.length > 0) {
    return { ok: false, report };
  }
  const extraction: SerializedExtraction = execution.extraction;
  return {
    ok: true,
    title: extraction.title,
    units: extraction.units.map(toBoundaryUnit),
  };
}
