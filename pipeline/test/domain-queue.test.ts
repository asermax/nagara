// Runs with standing miniflare teardown noise on the pool's stderr ("Engine
// was never started", "instance.not_found", "code had hung" cancellations):
// this file creates instances through POST /jobs, and the local runtime logs
// the expected rejections of the read path and the teardown of finished
// instances loudly, without failing any assertion. Anything NEW in that wall
// is worth investigating; the wall itself is the emulator, not the code.

import { reset, runDurableObjectAlarm, runInDurableObject } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";
import { scriptReply } from "../src/agents/settlement.ts";
import { jobIndexStub } from "../src/queue/job-index.ts";
import { articleHtml, passingRecipe } from "./fixtures/article.ts";
import {
  armAlarm,
  holdLease,
  postJob,
  queueFor,
  readLease,
  readWaiting,
  runToTerminal,
} from "./helpers/http.ts";
import { clearWorld, installWorld, slowRunWorld } from "./helpers/world.ts";

afterEach(async () => {
  clearWorld();
  await reset();
});

describe("domain queue", () => {
  it("creates the instance now when the lease is free, stores the busy id, and writes the index entry", async () => {
    installWorld(slowRunWorld(1500));
    const response = await postJob({
      job_id: "itm_a10",
      domain: "a10.example.com",
      recipe: passingRecipe,
    });
    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ state: "running" });

    expect(await readLease("a10.example.com")).toEqual({ jobId: "itm_a10" });
    await expect(env.EXTRACTION.get("itm_a10")).resolves.toBeTruthy();
    expect(await jobIndexStub(env).domainOf("itm_a10")).toBe("a10.example.com");

    await runToTerminal("itm_a10");
  }, 20000);

  it("holds a same-domain pair in the FIFO while the lease is taken, and it reads queued", async () => {
    await holdLease("a11.example.com", "busy-job");

    const second = await postJob({
      job_id: "itm_a11b",
      domain: "a11.example.com",
      recipe: passingRecipe,
    });
    expect(second.status).toBe(201);
    expect(await second.json()).toEqual({ state: "queued" });

    const third = await postJob({
      job_id: "itm_a11c",
      domain: "a11.example.com",
      recipe: passingRecipe,
    });
    expect(third.status).toBe(201);
    expect(await third.json()).toEqual({ state: "queued" });

    expect(await readWaiting("a11.example.com")).toEqual(["itm_a11b", "itm_a11c"]);
    expect(await queueFor("a11.example.com").stateOf("itm_a11b")).toBe("queued");
  });

  it("a different domain is a separate queue instance and both domains run", async () => {
    await holdLease("a12-first.example.com", "busy-job");

    const blocked = await postJob({
      job_id: "itm_a12a",
      domain: "a12-first.example.com",
      recipe: passingRecipe,
    });
    const running = await postJob({
      job_id: "itm_a12b",
      domain: "a12-second.example.com",
      recipe: passingRecipe,
    });
    expect(await blocked.json()).toEqual({ state: "queued" });
    expect(await running.json()).toEqual({ state: "running" });

    expect(await readWaiting("a12-first.example.com")).toEqual(["itm_a12a"]);
    await expect(env.EXTRACTION.get("itm_a12a")).rejects.toThrow();
    await expect(env.EXTRACTION.get("itm_a12b")).resolves.toBeTruthy();
  });

  it("a release from the workflow's last step creates the FIFO's next jobs in arrival order", async () => {
    installWorld(slowRunWorld(1500));
    await holdLease("a13.example.com", "itm_a13a");
    await postJob({ job_id: "itm_a13b", domain: "a13.example.com", recipe: passingRecipe });
    await postJob({ job_id: "itm_a13c", domain: "a13.example.com", recipe: passingRecipe });

    await queueFor("a13.example.com").release("itm_a13a");

    expect(await readLease("a13.example.com")).toEqual({ jobId: "itm_a13b" });
    expect(await readWaiting("a13.example.com")).toEqual(["itm_a13c"]);
    await expect(env.EXTRACTION.get("itm_a13b")).resolves.toBeTruthy();

    await runToTerminal("itm_a13b");
    expect(await readLease("a13.example.com")).toEqual({ jobId: "itm_a13c" });
    expect(await readWaiting("a13.example.com")).toEqual([]);
  }, 20000);

  it("the alarm sweeps a lease whose instance ended and creates the next job", async () => {
    await postJob({ job_id: "itm_a14a", domain: "a14.example.com", recipe: passingRecipe });
    await runToTerminal("itm_a14a");

    await holdLease("a14.example.com", "itm_a14a");
    await postJob({ job_id: "itm_a14b", domain: "a14.example.com", recipe: passingRecipe });
    await armAlarm("a14.example.com");

    expect(await runDurableObjectAlarm(queueFor("a14.example.com"))).toBe(true);
    expect(await readLease("a14.example.com")).toEqual({ jobId: "itm_a14b" });
    await expect(env.EXTRACTION.get("itm_a14b")).resolves.toBeTruthy();
  });

  it("the alarm sweeps a lease whose instance is unaddressable and creates the next job", async () => {
    await holdLease("a15.example.com", "itm_a15-ghost");
    await postJob({ job_id: "itm_a15b", domain: "a15.example.com", recipe: passingRecipe });
    await armAlarm("a15.example.com");

    expect(await runDurableObjectAlarm(queueFor("a15.example.com"))).toBe(true);
    expect(await readLease("a15.example.com")).toEqual({ jobId: "itm_a15b" });
    await expect(env.EXTRACTION.get("itm_a15b")).resolves.toBeTruthy();
  });

  it("the alarm re-arms over a running instance and sweeps nothing", async () => {
    installWorld(slowRunWorld(1500, { author: scriptReply(passingRecipe) }));

    await postJob({ job_id: "itm_a16", domain: "a16.example.com" });
    expect(await runDurableObjectAlarm(queueFor("a16.example.com"))).toBe(true);

    expect(await readLease("a16.example.com")).toEqual({ jobId: "itm_a16" });
    const alarm = await runInDurableObject(queueFor("a16.example.com"), (_instance, state) =>
      state.storage.getAlarm(),
    );
    expect(alarm).not.toBeNull();
    expect(alarm).toBeGreaterThan(Date.now());

    await runToTerminal("itm_a16");
  }, 20000);

  it("a create that throws persists no lease, and the next enqueue still creates", async () => {
    const failing = await queueFor("a17.example.com")
      .enqueue("bad id with spaces", { html: articleHtml, domain: "a17.example.com" })
      .then(
        () => "returned",
        (error: unknown) => `threw ${error instanceof Error ? error.message : String(error)}`,
      );
    expect(failing).toMatch(/creating the workflow failed|returned/);
    expect(await readLease("a17.example.com")).toBeUndefined();

    const next = await postJob({
      job_id: "itm_a17",
      domain: "a17.example.com",
      recipe: passingRecipe,
    });
    expect(next.status).toBe(201);
    expect(await readLease("a17.example.com")).toEqual({ jobId: "itm_a17" });
  });
});
