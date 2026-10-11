import { runDurableObjectAlarm, runInDurableObject } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { database, recipeVersions } from "@nagara/common";
import { asc, eq } from "drizzle-orm";
import { afterEach, describe, expect, it } from "vitest";
import { scriptReply } from "../src/agents/settlement.ts";
import { domainQueueStub } from "../src/queue/domain-queue.ts";
import { articleRecipe, failingRecipe } from "./fixtures/item-article.ts";
import { instanceIdOf, readRow, runItem, startItem } from "./helpers/item.ts";
import { logStatuses, scenario, statusesOf } from "./helpers/scenario.ts";
import { resetAgents, scriptAgents } from "./helpers/scripted-agents.ts";
import { useServer } from "./helpers/services.ts";

useServer();

const NOT_ARTICLE = '```json\n{"kind": "not-article"}\n```';
const GAVE_UP = '```json\n{"kind": "gave-up", "reason": "the markup changed past repair"}\n```';

afterEach(resetAgents);

const versionsOf = (domain: string) =>
  database(env.DB)
    .select({
      id: recipeVersions.id,
      version: recipeVersions.version,
      script: recipeVersions.script,
    })
    .from(recipeVersions)
    .where(eq(recipeVersions.domain, domain))
    .orderBy(asc(recipeVersions.version));

const recipeAttempts = async (itemId: string) =>
  (await statusesOf(itemId)).filter((status) => status === "generating recipe").length;

describe("the recipe step", () => {
  it("authors the first recipe of a new domain and saves it as version 1", async () => {
    scriptAgents({ author: scriptReply(articleRecipe) });

    await scenario({ itemId: "itm_000000c7", domain: "c7.test", recipe: null });
    await runItem("itm_000000c7", "complete");

    const [version, ...others] = await versionsOf("c7.test");

    expect(others).toEqual([]);
    expect(version).toMatchObject({ version: 1, script: articleRecipe });
    expect(await readRow("itm_000000c7")).toMatchObject({
      status: "ready",
      recipe_version_id: version.id,
    });
  });

  it("revises a recipe that fails the article and extracts with the new version", async () => {
    scriptAgents({ revision: scriptReply(articleRecipe) });

    await scenario({ itemId: "itm_000000c8", domain: "c8.test", recipe: failingRecipe });
    await runItem("itm_000000c8", "complete");

    const versions = await versionsOf("c8.test");

    expect(versions.map(({ version, script }) => [version, script])).toEqual([
      [1, failingRecipe],
      [2, articleRecipe],
    ]);
    expect(await readRow("itm_000000c8")).toMatchObject({
      status: "ready",
      recipe_version_id: versions[1].id,
    });
  });

  it("fails a not-article verdict in one attempt, saves nothing, and the alarm frees the lease", async () => {
    await logStatuses();
    scriptAgents({ author: NOT_ARTICLE });

    await scenario({ itemId: "itm_000000c9", domain: "c9.test", recipe: null });
    await runItem("itm_000000c9", "errored");

    expect(await readRow("itm_000000c9")).toMatchObject({
      status: "failed",
      current_step: "recipe",
      error: "the page is not an article",
    });
    expect(await recipeAttempts("itm_000000c9")).toBe(1);
    expect(await versionsOf("c9.test")).toEqual([]);

    await scenario({ itemId: "itm_000000ca", domain: "c9.test", recipe: null });

    const next = await startItem("itm_000000ca");

    await next.waitForStepResult({ name: "lease" });

    const queue = domainQueueStub(env, "c9.test");

    expect(await runDurableObjectAlarm(queue)).toBe(true);
    expect(await runInDurableObject(queue, (_, state) => state.storage.kv.get("lease"))).toBe(
      instanceIdOf("itm_000000ca"),
    );
  });

  it("fails when the revision gives up and leaves the old version current", async () => {
    scriptAgents({ revision: GAVE_UP });

    await scenario({ itemId: "itm_000000cb", domain: "c10.test", recipe: failingRecipe });
    await runItem("itm_000000cb", "errored");

    expect(await readRow("itm_000000cb")).toMatchObject({
      status: "failed",
      current_step: "recipe",
      error: "revision gave up: the recipe still fails the article and the old version stands",
      recipe_version_id: null,
    });
    expect((await versionsOf("c10.test")).map(({ version }) => version)).toEqual([1]);
  });
});
