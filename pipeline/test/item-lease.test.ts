import { runInDurableObject } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { createRecipeVersion, database } from "@nagara/common";
import { and, eq, min } from "drizzle-orm";
import { describe, expect, it } from "vitest";
import { domainQueueStub } from "../src/queue/domain-queue.ts";
import { articleHtml, articleRecipe } from "./fixtures/item-article.ts";
import { insertItem, instanceIdOf, readRow, runItem, startItem } from "./helpers/item.ts";
import { logStatuses, scenario, statusLog } from "./helpers/scenario.ts";
import {
  codeDescribe,
  firecrawlCassette,
  firecrawlPage,
  modal,
  replay,
  requests,
  server,
  useServer,
} from "./helpers/services.ts";

useServer();

const seqOf = async (itemId: string, status: string, step: string) =>
  (
    await database(env.DB)
      .select({ seq: min(statusLog.seq) })
      .from(statusLog)
      .where(
        and(
          eq(statusLog.item_id, itemId),
          eq(statusLog.status, status),
          eq(statusLog.current_step, step),
        ),
      )
      .get()
  )?.seq ?? 0;

describe("the domain lease", () => {
  it("holds a second item of the same domain queued until the first releases after its recipe", async () => {
    await logStatuses();

    const items = ["itm_000000c5", "itm_000000c6"];
    const urls = items.map((itemId) => `https://c5.test/${itemId}`);

    await createRecipeVersion(database(env.DB), { domain: "c5.test", script: articleRecipe });

    for (const [index, itemId] of items.entries()) {
      await insertItem(itemId, urls[index]);
    }

    server.use(
      ...modal().handlers,
      ...replay(
        ...urls.map((url) => firecrawlCassette(url, [firecrawlPage(articleHtml(), url)])),
        codeDescribe,
        codeDescribe,
      ),
    );

    const instances = await Promise.all(items.map((itemId) => startItem(itemId)));

    await Promise.all(instances.map((instance) => instance.waitForStatus("complete")));

    const [first, second] =
      (await seqOf(items[0], "generating", "recipe")) <
      (await seqOf(items[1], "generating", "recipe"))
        ? items
        : [...items].reverse();

    expect(await seqOf(second, "queued", "lease")).toBeLessThan(
      await seqOf(first, "generating", "release"),
    );
    expect(await seqOf(second, "generating", "recipe")).toBeGreaterThan(
      await seqOf(first, "generating", "release"),
    );
    expect((await readRow(first)).status).toBe("ready");
    expect((await readRow(second)).status).toBe("ready");
  });

  it("fails in lease after three waits behind a holder that never releases", async () => {
    await runInDurableObject(domainQueueStub(env, "c6.test"), (_, state) => {
      state.storage.kv.put("lease", "wf-never-releases");
    });
    await scenario({ itemId: "itm_000000c7", domain: "c6.test" });

    await runItem("itm_000000c7", "errored", async (modifier) => {
      for (const wait of [1, 2, 3]) {
        await modifier.forceEventTimeout({ name: `lease wait ${wait}` });
      }
    });

    expect(await readRow("itm_000000c7")).toMatchObject({
      status: "failed",
      current_step: "lease",
      error: "the domain's lease was not granted after 3 waits",
    });
  });

  it("restarts a recipe failure from lease, granted again while still the holder, with the current recipe", async () => {
    const itemId = "itm_000000c8";

    await scenario({ itemId, domain: "c20.test", recipe: null });

    const instance = await runItem(itemId, "errored");

    expect((await readRow(itemId)).current_step).toBe("recipe");
    expect(
      await runInDurableObject(domainQueueStub(env, "c20.test"), (_, state) =>
        state.storage.kv.get("lease"),
      ),
    ).toBe(instanceIdOf(itemId));

    const { id: recipeVersionId } = await createRecipeVersion(database(env.DB), {
      domain: "c20.test",
      script: articleRecipe,
    });

    await (await env.ITEM_WORKFLOW.get(instanceIdOf(itemId))).restart({ from: { name: "lease" } });
    await instance.waitForStatus("complete");

    expect(await readRow(itemId)).toMatchObject({
      status: "ready",
      recipe_version_id: recipeVersionId,
      error: null,
    });
    expect(requests.filter((request) => request.includes("api.firecrawl.dev"))).toHaveLength(1);
  });
});
