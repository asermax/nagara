import { introspectWorkflowInstance } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { type ItemRow, readItem } from "@nagara/common";
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

  await env.DB.prepare(
    `INSERT INTO items (id, url, voice, status, created_at, updated_at, queued_at)
     VALUES (?, ?, ?, 'queued', ?, ?, ?)`,
  )
    .bind(id, url, voice, now, now, now)
    .run();
};

export const readRow = async (id: string) => (await readItem(env.DB, id)) as ItemRow;

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

export const costsOf = async (itemId: string) =>
  (
    await env.DB.prepare(
      "SELECT type, quantity, cached FROM cost_entries WHERE item_id = ? ORDER BY created_at",
    )
      .bind(itemId)
      .all<{ type: string; quantity: number; cached: number }>()
  ).results;
