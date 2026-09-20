import { reset } from "cloudflare:test";
import { env, exports } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";
import { articleHtml, passingRecipe } from "./fixtures/article.ts";

async function postJob(body: unknown): Promise<Response> {
  return await exports.default.fetch(
    new Request("https://pipeline.test/jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

afterEach(async () => {
  await reset();
});

describe("POST /jobs", () => {
  it("A1: accepts a fresh job within the cap and routes it to the domain's queue", async () => {
    const response = await postJob({
      html: articleHtml,
      recipe: passingRecipe,
      job_id: "itm_a1",
      domain: "a1.example.com",
    });
    expect(response.status).toBe(201);
    const body = (await response.json()) as { state: string };
    expect(body.state).toBe("running");

    const indexId = env.JOB_INDEX.idFromName("nagara-job-index");
    const entry = await env.JOB_INDEX.get(indexId).fetch("https://index/entries/itm_a1");
    expect(entry.status).toBe(200);
    expect(await entry.json()).toEqual({ domain: "a1.example.com" });

    await expect(env.EXTRACTION.get("itm_a1")).resolves.toBeTruthy();
  });

  it("A2: rejects html over the cap with 413 and creates no job", async () => {
    const oversized = "a".repeat(1048576 + 1);
    const response = await postJob({
      html: oversized,
      job_id: "itm_a2",
      domain: "a2.example.com",
    });
    expect(response.status).toBe(413);

    const indexId = env.JOB_INDEX.idFromName("nagara-job-index");
    const entry = await env.JOB_INDEX.get(indexId).fetch("https://index/entries/itm_a2");
    expect(entry.status).toBe(404);
    await expect(env.EXTRACTION.get("itm_a2")).rejects.toThrow();
  });

  it("A3: answers 409 for an existing id, restarting nothing, and the id keeps answering", async () => {
    const create = {
      html: articleHtml,
      recipe: passingRecipe,
      job_id: "itm_a3",
      domain: "a3.example.com",
    };
    const first = await postJob(create);
    expect(first.status).toBe(201);

    const again = await postJob(create);
    expect(again.status).toBe(409);

    const read = await exports.default.fetch(new Request("https://pipeline.test/jobs/itm_a3"));
    expect(read.status).toBe(200);
    const body = (await read.json()) as { state: string };
    expect(["running", "complete"]).toContain(body.state);
  });
});
