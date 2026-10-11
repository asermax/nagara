import { introspectWorkflowInstance } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { costEntries, database, getItem, type ItemRow, items } from "@nagara/common";
import { asc, eq } from "drizzle-orm";
import { afterEach } from "vitest";

type Introspector = Awaited<ReturnType<typeof introspectWorkflowInstance>>;
type Modifier = Parameters<Parameters<Introspector["modify"]>[0]>[0];

const introspectors: Introspector[] = [];

// Each introspector is disposed after its test, so its mocks and modifications never reach the
// next test's instances.
afterEach(async () => {
  await Promise.all(introspectors.splice(0).map((introspector) => introspector.dispose()));
});

export const insertItem = async (id: string, url: string, voice = "af_heart") => {
  const now = new Date().toISOString();

  await database(env.DB)
    .insert(items)
    .values({ id, url, voice, status: "queued", created_at: now, updated_at: now, queued_at: now });
};

export const readRow = async (id: string) => (await getItem(database(env.DB), id)) as ItemRow;

export const instanceIdOf = (itemId: string) => `wf-${itemId}`;

// Sleeps and retry backoff are skipped, so a step's three attempts run back to back.
export const startItem = async (itemId: string, modify?: (modifier: Modifier) => Promise<void>) => {
  const instance = await introspectWorkflowInstance(env.ITEM_WORKFLOW, instanceIdOf(itemId));

  introspectors.push(instance);

  await instance.modify(async (modifier) => {
    await modifier.disableSleeps();
    await modifier.disableRetryDelays();
    await modify?.(modifier);
  });
  await env.ITEM_WORKFLOW.create({ id: instanceIdOf(itemId), params: { itemId } });

  return instance;
};

export const runItem = async (
  itemId: string,
  status: "complete" | "errored",
  modify?: (modifier: Modifier) => Promise<void>,
) => {
  const instance = await startItem(itemId, modify);

  await instance.waitForStatus(status);

  return instance;
};

export const costsOf = (itemId: string) =>
  database(env.DB)
    .select({
      type: costEntries.type,
      quantity: costEntries.quantity,
      cached: costEntries.cached,
    })
    .from(costEntries)
    .where(eq(costEntries.item_id, itemId))
    .orderBy(asc(costEntries.created_at));
