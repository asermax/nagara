import { runDurableObjectAlarm, runInDurableObject } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { describe, expect, it } from "vitest";
import { domainQueueStub } from "../src/queue/domain-queue.ts";
import { articleHtml } from "./fixtures/item-article.ts";
import { insertItem, instanceIdOf, readRow, startItem } from "./helpers/item.ts";
import { firecrawlCassette, firecrawlPage, replay, server, useServer } from "./helpers/services.ts";

useServer();

const readQueue = (domain: string) =>
  runInDurableObject(domainQueueStub(env, domain), (_, state) => ({
    lease: state.storage.kv.get<string>("lease") ?? null,
    waiting: state.storage.kv.get<string[]>("waiting") ?? [],
  }));

const holdLease = (domain: string, holder: string, waiting: string[] = []) =>
  runInDurableObject(domainQueueStub(env, domain), (_, state) => {
    state.storage.kv.put("lease", holder);
    state.storage.kv.put("waiting", waiting);
  });

const alarmOf = (domain: string) =>
  runInDurableObject(domainQueueStub(env, domain), (_, state) => state.storage.getAlarm());

const endedInstance = async (id: string) => {
  const instance = await env.ITEM_WORKFLOW.create({ id, params: { itemId: `itm_${id}` } });

  await instance.terminate();

  return id;
};

// An item whose lease step found the domain busy: it waits for lease-granted with nothing scripted
// past the lease, so the wait is all it does.
const waitingItem = async (itemId: string, domain: string) => {
  const url = `https://${domain}/${itemId}`;

  await insertItem(itemId, url);
  server.use(...replay(firecrawlCassette(url, [firecrawlPage(articleHtml(), url)])));

  const instance = await startItem(itemId);

  await instance.waitForStepResult({ name: "lease" });

  return instance;
};

describe("domain queue", () => {
  it("grants a free lease and arms the alarm", async () => {
    const queue = domainQueueStub(env, "free.test");

    expect(await queue.acquire("wf-a")).toEqual({ granted: true });
    expect(await readQueue("free.test")).toEqual({ lease: "wf-a", waiting: [] });
    expect(await alarmOf("free.test")).toBeGreaterThan(Date.now());
  });

  it("refuses a held lease and appends the id to the queue", async () => {
    await holdLease("held.test", "wf-holder");

    expect(await domainQueueStub(env, "held.test").acquire("wf-b")).toEqual({ granted: false });
    expect(await readQueue("held.test")).toEqual({ lease: "wf-holder", waiting: ["wf-b"] });
  });

  it("grants the lease again to the instance that holds it", async () => {
    await holdLease("again.test", "wf-holder", ["wf-c"]);

    expect(await domainQueueStub(env, "again.test").acquire("wf-holder")).toEqual({
      granted: true,
    });
    expect(await readQueue("again.test")).toEqual({ lease: "wf-holder", waiting: ["wf-c"] });
  });

  it("keeps a waiter's place when it asks again", async () => {
    await holdLease("place.test", "wf-holder", ["wf-d", "wf-e"]);

    expect(await domainQueueStub(env, "place.test").acquire("wf-d")).toEqual({ granted: false });
    expect(await readQueue("place.test")).toEqual({
      lease: "wf-holder",
      waiting: ["wf-d", "wf-e"],
    });
  });

  it("hands the released lease to the next live waiter, skipping one that ended", async () => {
    const domain = "handoff.test";
    const ended = await endedInstance("ended-handoff");

    await holdLease(domain, "wf-holder", [ended]);

    const waiter = await waitingItem("itm_000000a1", domain);

    expect((await readQueue(domain)).waiting).toEqual([ended, instanceIdOf("itm_000000a1")]);

    await domainQueueStub(env, domain).release("wf-holder");

    expect(await readQueue(domain)).toEqual({ lease: instanceIdOf("itm_000000a1"), waiting: [] });
    await waiter.waitForStatus("errored");
    expect((await readRow("itm_000000a1")).current_step).toBe("recipe");
  });

  it("drops a waiter that releases from the queue and leaves the lease alone", async () => {
    await holdLease("leave.test", "wf-holder", ["wf-f", "wf-g"]);

    await domainQueueStub(env, "leave.test").release("wf-f");

    expect(await readQueue("leave.test")).toEqual({ lease: "wf-holder", waiting: ["wf-g"] });
  });

  it("sweeps the lease of an ended holder on the alarm and grants the next waiter", async () => {
    const domain = "sweep.test";
    const ended = await endedInstance("ended-sweep");

    await domainQueueStub(env, domain).acquire(ended);

    const waiter = await waitingItem("itm_000000a2", domain);

    expect(await runDurableObjectAlarm(domainQueueStub(env, domain))).toBe(true);
    expect(await readQueue(domain)).toEqual({ lease: instanceIdOf("itm_000000a2"), waiting: [] });
    await waiter.waitForStatus("errored");
    expect((await readRow("itm_000000a2")).current_step).toBe("recipe");
  });

  it("re-arms the alarm over a holder that is still running", async () => {
    const domain = "running.test";

    await holdLease(domain, "wf-holder");
    await waitingItem("itm_000000a3", domain);
    await holdLease(domain, instanceIdOf("itm_000000a3"));
    await runInDurableObject(domainQueueStub(env, domain), (_, state) =>
      state.storage.setAlarm(Date.now() + 1000),
    );

    expect(await runDurableObjectAlarm(domainQueueStub(env, domain))).toBe(true);
    expect(await readQueue(domain)).toEqual({ lease: instanceIdOf("itm_000000a3"), waiting: [] });
    expect(await alarmOf(domain)).toBeGreaterThan(Date.now());
  });
});
