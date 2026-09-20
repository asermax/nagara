import { introspectWorkflowInstance, reset, runInDurableObject } from "cloudflare:test";
import { env, exports } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";
import type { JobStatusBody } from "../src/http/job-status.ts";
import { articleHtml, failingRecipe, passingRecipe } from "./fixtures/article.ts";
import {
  clearWorld,
  GAVE_UP_REPLY,
  installWorld,
  NOT_ARTICLE_REPLY,
  scriptReplyText,
  slowRunWorld,
  worldWithAgents,
} from "./helpers/world.ts";

afterEach(async () => {
  clearWorld();
  await reset();
});

async function getJob(jobId: string): Promise<JobStatusBody> {
  const response = await exports.default.fetch(new Request(`https://pipeline.test/jobs/${jobId}`));
  expect(response.status).toBe(200);
  return (await response.json()) as JobStatusBody;
}

async function postJob(jobId: string, domain: string, recipe?: string): Promise<Response> {
  return await exports.default.fetch(
    new Request("https://pipeline.test/jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ html: articleHtml, recipe, job_id: jobId, domain }),
    }),
  );
}

describe("GET /jobs/{job_id}", () => {
  it("A4: a complete job whose recipe was provided answers title and units with no recipe member", async () => {
    await postJob("read_a4", "read-a4.example.com", passingRecipe);
    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a4");
    await instance.waitForStatus("complete");

    const body = await getJob("read_a4");
    expect(body.state).toBe("complete");
    expect(body.title).toBe("Colorless Green Ideas");
    expect(body.units?.length).toBe(5);
    expect("recipe" in body).toBe(false);
  });

  it("A5: a complete job after authoring answers title, units, and the recipe", async () => {
    installWorld(worldWithAgents({ author: scriptReplyText(passingRecipe) }));
    await postJob("read_a5", "read-a5.example.com");
    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a5");
    await instance.waitForStatus("complete");

    const body = await getJob("read_a5");
    expect(body.state).toBe("complete");
    expect(body.title).toBe("Colorless Green Ideas");
    expect(body.recipe).toBe(passingRecipe);
  });

  it("A6: a running job answers the state alone", async () => {
    installWorld(slowRunWorld(1500, { author: scriptReplyText(passingRecipe) }));
    await postJob("read_a6", "read-a6.example.com");

    const body = await getJob("read_a6");
    expect(body).toEqual({ state: "running" });

    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a6");
    await instance.waitForStatus("complete");
  }, 20000);

  it("A7: a job waiting in the FIFO reads queued through the index and the domain queue", async () => {
    const stub = env.DOMAIN_QUEUE.get(env.DOMAIN_QUEUE.idFromName("read-a7.example.com"));
    await runInDurableObject(stub, (_instance, state) =>
      state.storage.put("lease", { jobId: "holder-job" }),
    );

    const response = await postJob("read_a7", "read-a7.example.com");
    expect(await response.json()).toEqual({ state: "queued" });

    const body = await getJob("read_a7");
    expect(body).toEqual({ state: "queued" });
  });

  it("A8: a not-article job answers the state alone", async () => {
    installWorld(worldWithAgents({ author: NOT_ARTICLE_REPLY }));
    await postJob("read_a8", "read-a8.example.com");
    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a8");
    await instance.waitForStatus("complete");

    const body = await getJob("read_a8");
    expect(body).toEqual({ state: "not_article" });
  });

  it("A9: an error job answers the service's error string", async () => {
    installWorld(worldWithAgents({ revision: GAVE_UP_REPLY }));
    await postJob("read_a9", "read-a9.example.com", failingRecipe);
    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a9");
    await instance.waitForStatus("complete");

    const body = await getJob("read_a9");
    expect(body.state).toBe("error");
    expect(body.error).toMatch(/revision gave up/);
  });
});
