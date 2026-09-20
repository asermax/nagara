// Runs with standing miniflare teardown noise on the pool's stderr ("Engine
// was never started", "instance.not_found", "code had hung" cancellations):
// this file creates instances through POST /jobs, and the local runtime logs
// the expected rejections of the read path and the teardown of finished
// instances loudly, without failing any assertion. Anything NEW in that wall
// is worth investigating; the wall itself is the emulator, not the code.

import { reset } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";
import { jobIndexStub } from "../src/queue/job-index.ts";
import { articleHtml, passingRecipe } from "./fixtures/article.ts";
import { getJob, postJob } from "./helpers/http.ts";

afterEach(async () => {
  await reset();
});

describe("POST /jobs", () => {
  it("accepts a fresh job within the cap and routes it to the domain's queue", async () => {
    const response = await postJob({
      html: articleHtml,
      recipe: passingRecipe,
      job_id: "itm_a1",
      domain: "a1.example.com",
    });
    expect(response.status).toBe(201);
    const body = (await response.json()) as { state: string };
    expect(body.state).toBe("running");

    expect(await jobIndexStub(env).domainOf("itm_a1")).toBe("a1.example.com");
    await expect(env.EXTRACTION.get("itm_a1")).resolves.toBeTruthy();
  });

  it("rejects html over the cap with 413 and creates no job", async () => {
    const oversized = "a".repeat(1048576 + 1);
    const response = await postJob({
      html: oversized,
      job_id: "itm_a2",
      domain: "a2.example.com",
    });
    expect(response.status).toBe(413);

    expect(await jobIndexStub(env).domainOf("itm_a2")).toBeNull();
    await expect(env.EXTRACTION.get("itm_a2")).rejects.toThrow();
  });

  it("answers 409 for an existing id, restarting nothing, and the id keeps answering", async () => {
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

    const body = await getJob("itm_a3");
    expect(["running", "complete"]).toContain(body.state);
  });
});
