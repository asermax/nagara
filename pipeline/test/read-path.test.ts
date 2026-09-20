// Runs with standing miniflare teardown noise on the pool's stderr ("Engine
// was never started", "instance.not_found", "code had hung" cancellations):
// this file creates instances through POST /jobs, and the local runtime logs
// the expected rejections of the read path and the teardown of finished
// instances loudly, without failing any assertion. Anything NEW in that wall
// is worth investigating; the wall itself is the emulator, not the code.

import { introspectWorkflowInstance, reset } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";
import { scriptReply } from "../src/agents/settlement.ts";
import { articleHtml, failingRecipe, passingRecipe } from "./fixtures/article.ts";
import { getJob, holdLease, postJob } from "./helpers/http.ts";
import {
  clearWorld,
  GAVE_UP_REPLY,
  installWorld,
  NOT_ARTICLE_REPLY,
  slowRunWorld,
  worldWithAgents,
} from "./helpers/world.ts";

afterEach(async () => {
  clearWorld();
  await reset();
});

describe("GET /jobs/{job_id}", () => {
  it("a complete job whose recipe was provided answers title and units with no recipe member", async () => {
    await postJob({ job_id: "read_a4", domain: "read-a4.example.com", recipe: passingRecipe });
    // The introspector stays open across the GET: miniflare tears a completed
    // instance's engine down once its last reference goes, while the real
    // platform answers status for the retention window.
    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a4");
    await instance.waitForStatus("complete");

    const body = await getJob("read_a4");
    expect(body.state).toBe("complete");
    expect(body.title).toBe("Colorless Green Ideas");
    expect(body.units?.length).toBe(5);
    expect("recipe" in body).toBe(false);
  });

  it("a complete job after authoring answers title, units, and the recipe", async () => {
    installWorld(worldWithAgents({ author: scriptReply(passingRecipe) }));
    await postJob({ job_id: "read_a5", domain: "read-a5.example.com" });
    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a5");
    await instance.waitForStatus("complete");

    const body = await getJob("read_a5");
    expect(body.state).toBe("complete");
    expect(body.title).toBe("Colorless Green Ideas");
    expect(body.recipe).toBe(passingRecipe);
  });

  it("a running job answers the state alone", async () => {
    installWorld(slowRunWorld(1500, { author: scriptReply(passingRecipe) }));
    await postJob({ job_id: "read_a6", domain: "read-a6.example.com" });

    const body = await getJob("read_a6");
    expect(body).toEqual({ state: "running" });

    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a6");
    await instance.waitForStatus("complete");
  }, 20000);

  it("a job waiting in the FIFO reads queued through the index and the domain queue", async () => {
    await holdLease("read-a7.example.com", "holder-job");

    const response = await postJob({
      job_id: "read_a7",
      domain: "read-a7.example.com",
      html: articleHtml,
    });
    expect(await response.json()).toEqual({ state: "queued" });

    const body = await getJob("read_a7");
    expect(body).toEqual({ state: "queued" });
  });

  it("a not-article job answers the state alone", async () => {
    installWorld(worldWithAgents({ author: NOT_ARTICLE_REPLY }));
    await postJob({ job_id: "read_a8", domain: "read-a8.example.com" });
    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a8");
    await instance.waitForStatus("complete");

    const body = await getJob("read_a8");
    expect(body).toEqual({ state: "not_article" });
  });

  it("an error job answers the service's error string", async () => {
    installWorld(worldWithAgents({ revision: GAVE_UP_REPLY }));
    await postJob({ job_id: "read_a9", domain: "read-a9.example.com", recipe: failingRecipe });
    await using instance = await introspectWorkflowInstance(env.EXTRACTION, "read_a9");
    await instance.waitForStatus("complete");

    const body = await getJob("read_a9");
    expect(body.state).toBe("error");
    expect(body.error).toMatch(/revision gave up/);
  });
});
