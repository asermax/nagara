import {
  introspectWorkflowInstance,
  reset,
  runDurableObjectAlarm,
  runInDurableObject,
} from "cloudflare:test";
import { env, exports } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";
import { articleHtml, passingRecipe } from "./fixtures/article.ts";
import { clearWorld, installWorld, scriptReplyText, slowRunWorld } from "./helpers/world.ts";

afterEach(async () => {
  clearWorld();
  await reset();
});

function queueFor(domain: string) {
  return env.DOMAIN_QUEUE.get(env.DOMAIN_QUEUE.idFromName(domain));
}

async function enqueue(domain: string, jobId: string, recipe?: string): Promise<Response> {
  return await exports.default.fetch(
    new Request("https://pipeline.test/jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ html: articleHtml, recipe, job_id: jobId, domain }),
    }),
  );
}

async function readLease(domain: string): Promise<{ jobId: string } | undefined> {
  return await runInDurableObject(queueFor(domain), (_instance, state) =>
    state.storage.get<{ jobId: string }>("lease"),
  );
}

async function readFifo(domain: string): Promise<{ jobId: string }[]> {
  return (await runInDurableObject(queueFor(domain), (_instance, state) =>
    state.storage.get<{ jobId: string }[]>("fifo"),
  )) as { jobId: string }[];
}

async function holdLease(domain: string, jobId: string): Promise<void> {
  await runInDurableObject(queueFor(domain), (_instance, state) =>
    state.storage.put("lease", { jobId }),
  );
}

describe("domain queue", () => {
  it("A10: creates the instance now when the lease is free, stores the busy id, and writes the index entry", async () => {
    const response = await enqueue("a10.example.com", "itm_a10", passingRecipe);
    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ state: "running" });

    expect(await readLease("a10.example.com")).toEqual({ jobId: "itm_a10" });
    await expect(env.EXTRACTION.get("itm_a10")).resolves.toBeTruthy();

    const indexId = env.JOB_INDEX.idFromName("nagara-job-index");
    const entry = await env.JOB_INDEX.get(indexId).fetch("https://index/entries/itm_a10");
    expect(await entry.json()).toEqual({ domain: "a10.example.com" });
  });

  it("A11: holds a same-domain pair in the FIFO while the lease is taken, and it reads queued", async () => {
    await holdLease("a11.example.com", "busy-job");

    const second = await enqueue("a11.example.com", "itm_a11b", passingRecipe);
    expect(second.status).toBe(201);
    expect(await second.json()).toEqual({ state: "queued" });

    const third = await enqueue("a11.example.com", "itm_a11c", passingRecipe);
    expect(third.status).toBe(201);
    expect(await third.json()).toEqual({ state: "queued" });

    expect((await readFifo("a11.example.com")).map((entry) => entry.jobId)).toEqual([
      "itm_a11b",
      "itm_a11c",
    ]);

    const state = await queueFor("a11.example.com").fetch("https://queue/state/itm_a11b");
    expect(await state.json()).toEqual({ state: "queued" });
  });

  it("A12: a different domain is a separate queue instance and both domains run", async () => {
    await holdLease("a12-first.example.com", "busy-job");

    const blocked = await enqueue("a12-first.example.com", "itm_a12a", passingRecipe);
    const running = await enqueue("a12-second.example.com", "itm_a12b", passingRecipe);
    expect(await blocked.json()).toEqual({ state: "queued" });
    expect(await running.json()).toEqual({ state: "running" });

    expect((await readFifo("a12-first.example.com")).map((entry) => entry.jobId)).toEqual([
      "itm_a12a",
    ]);
    await expect(env.EXTRACTION.get("itm_a12a")).rejects.toThrow();
    await expect(env.EXTRACTION.get("itm_a12b")).resolves.toBeTruthy();
  });

  it("A13: a release from the workflow's last step creates the FIFO's next jobs in arrival order", async () => {
    await holdLease("a13.example.com", "itm_a13a");
    await runInDurableObject(queueFor("a13.example.com"), (_instance, state) =>
      state.storage.put("fifo", [
        {
          jobId: "itm_a13b",
          params: { html: articleHtml, recipe: passingRecipe, domain: "a13.example.com" },
        },
        {
          jobId: "itm_a13c",
          params: { html: articleHtml, recipe: passingRecipe, domain: "a13.example.com" },
        },
      ]),
    );

    const firstRelease = await queueFor("a13.example.com").fetch("https://queue/release", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ job_id: "itm_a13a" }),
    });
    expect(firstRelease.status).toBe(200);

    expect(await readLease("a13.example.com")).toEqual({ jobId: "itm_a13b" });
    expect((await readFifo("a13.example.com")).map((entry) => entry.jobId)).toEqual(["itm_a13c"]);
    await expect(env.EXTRACTION.get("itm_a13b")).resolves.toBeTruthy();

    await using secondInstance = await introspectWorkflowInstance(env.EXTRACTION, "itm_a13b");
    await secondInstance.waitForStatus("complete");
    expect(await readLease("a13.example.com")).toEqual({ jobId: "itm_a13c" });
    expect(await readFifo("a13.example.com")).toEqual([]);
  });

  it("A14: the alarm sweeps a lease whose instance ended and creates the next job", async () => {
    await enqueue("a14.example.com", "itm_a14a", passingRecipe);
    await using ended = await introspectWorkflowInstance(env.EXTRACTION, "itm_a14a");
    await ended.waitForStatus("complete");

    await holdLease("a14.example.com", "itm_a14a");
    await runInDurableObject(queueFor("a14.example.com"), (_instance, state) =>
      state.storage.put("fifo", [
        { jobId: "itm_a14b", params: { html: articleHtml, domain: "a14.example.com" } },
      ]),
    );
    await runInDurableObject(queueFor("a14.example.com"), (_instance, state) =>
      state.storage.setAlarm(Date.now() + 60000),
    );

    expect(await runDurableObjectAlarm(queueFor("a14.example.com"))).toBe(true);
    expect(await readLease("a14.example.com")).toEqual({ jobId: "itm_a14b" });
    await expect(env.EXTRACTION.get("itm_a14b")).resolves.toBeTruthy();
  });

  it("A15: the alarm sweeps a lease whose instance is unaddressable and creates the next job", async () => {
    await holdLease("a15.example.com", "itm_a15-ghost");
    await runInDurableObject(queueFor("a15.example.com"), (_instance, state) =>
      state.storage.put("fifo", [
        { jobId: "itm_a15b", params: { html: articleHtml, domain: "a15.example.com" } },
      ]),
    );
    await runInDurableObject(queueFor("a15.example.com"), (_instance, state) =>
      state.storage.setAlarm(Date.now() + 60000),
    );

    expect(await runDurableObjectAlarm(queueFor("a15.example.com"))).toBe(true);
    expect(await readLease("a15.example.com")).toEqual({ jobId: "itm_a15b" });
    await expect(env.EXTRACTION.get("itm_a15b")).resolves.toBeTruthy();
  });

  it("A16: the alarm re-arms over a running instance and sweeps nothing", async () => {
    installWorld(slowRunWorld(1500, { author: scriptReplyText(passingRecipe) }));

    await enqueue("a16.example.com", "itm_a16");
    expect(await runDurableObjectAlarm(queueFor("a16.example.com"))).toBe(true);

    expect(await readLease("a16.example.com")).toEqual({ jobId: "itm_a16" });
    const alarm = await runInDurableObject(queueFor("a16.example.com"), (_instance, state) =>
      state.storage.getAlarm(),
    );
    expect(alarm).not.toBeNull();
    expect(alarm).toBeGreaterThan(Date.now());

    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "itm_a16");
    await instance.waitForStatus("complete");
  }, 20000);

  it("A17: a create that throws persists no lease, and the next enqueue still creates", async () => {
    const failing = await queueFor("a17.example.com")
      .fetch("https://queue/enqueue", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          job_id: "bad id with spaces",
          params: { html: articleHtml, domain: "a17.example.com" },
        }),
      })
      .then(
        (response) => response.status,
        () => -1,
      );
    expect([500, -1]).toContain(failing);
    expect(await readLease("a17.example.com")).toBeUndefined();

    const next = await enqueue("a17.example.com", "itm_a17", passingRecipe);
    expect(next.status).toBe(201);
    expect(await readLease("a17.example.com")).toEqual({ jobId: "itm_a17" });
  });
});
