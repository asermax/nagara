import { introspectWorkflowInstance, reset } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";
import type { JobStatusBody } from "../src/http/job-status.ts";
import { articleHtml, failingRecipe, passingRecipe } from "./fixtures/article.ts";
import {
  clearWorld,
  GAVE_UP_REPLY,
  installWorld,
  NOT_ARTICLE_REPLY,
  scriptReplyText,
  worldWithAgents,
} from "./helpers/world.ts";

afterEach(async () => {
  clearWorld();
  await reset();
});

async function runToTerminal(jobId: string): Promise<JobStatusBody> {
  await using instance = await introspectWorkflowInstance(env.EXTRACTION, jobId);
  await instance.waitForStatus("complete");
  return (await instance.getOutput()) as JobStatusBody;
}

async function leaseOf(domain: string): Promise<{ jobId: string } | undefined> {
  const stub = env.DOMAIN_QUEUE.get(env.DOMAIN_QUEUE.idFromName(domain));
  const { runInDurableObject } = await import("cloudflare:test");
  return await runInDurableObject(stub, (_instance, state) =>
    state.storage.get<{ jobId: string }>("lease"),
  );
}

describe("extraction workflow", () => {
  it("A20: a provided recipe that validates outright completes with title and units, no recipe member, and its last step releases the lease", async () => {
    await env.EXTRACTION.create({
      id: "wf_a20",
      params: { html: articleHtml, recipe: passingRecipe, domain: "a20.example.com" },
    });
    const output = await runToTerminal("wf_a20");

    expect(output.state).toBe("complete");
    expect(output.title).toBe("Colorless Green Ideas");
    expect(output.units?.length).toBe(5);
    expect("recipe" in output).toBe(false);
    expect(await leaseOf("a20.example.com")).toBeUndefined();
  });

  it("A21: a provided recipe that fails validation is revised by the agent and completes carrying the recipe", async () => {
    installWorld(worldWithAgents({ revision: scriptReplyText(passingRecipe) }));
    await env.EXTRACTION.create({
      id: "wf_a21",
      params: { html: articleHtml, recipe: failingRecipe, domain: "a21.example.com" },
    });
    const output = await runToTerminal("wf_a21");

    expect(output.state).toBe("complete");
    expect(output.recipe).toBe(passingRecipe);
    expect(output.title).toBe("Colorless Green Ideas");
  });

  it("A22: revision exhausting its retries ends in error with the service's string", async () => {
    let revisionDispatches = 0;
    installWorld(
      worldWithAgents({
        revision: GAVE_UP_REPLY,
        onRevisionDispatch: () => (revisionDispatches += 1),
      }),
    );
    await env.EXTRACTION.create({
      id: "wf_a22",
      params: { html: articleHtml, recipe: failingRecipe, domain: "a22.example.com" },
    });
    const output = await runToTerminal("wf_a22");

    expect(output.state).toBe("error");
    expect(output.error).toMatch(/revision gave up/);
    expect(revisionDispatches).toBe(3);
  });

  it("A23: an absent recipe authors one, and the settled script runs through the runtime to complete", async () => {
    installWorld(worldWithAgents({ author: scriptReplyText(passingRecipe) }));
    await env.EXTRACTION.create({
      id: "wf_a23",
      params: { html: articleHtml, domain: "a23.example.com" },
    });
    const output = await runToTerminal("wf_a23");

    expect(output.state).toBe("complete");
    expect(output.recipe).toBe(passingRecipe);
    expect(output.units?.length).toBe(5);
  });

  it("A24: the author's not-article verdict ends the job with nothing saved", async () => {
    installWorld(worldWithAgents({ author: NOT_ARTICLE_REPLY }));
    await env.EXTRACTION.create({
      id: "wf_a24",
      params: { html: articleHtml, domain: "a24.example.com" },
    });
    const output = await runToTerminal("wf_a24");

    expect(output).toEqual({ state: "not_article" });
  });

  it("A25: authoring exhausting its one retry ends in error with the service's string", async () => {
    let authorDispatches = 0;
    installWorld(
      worldWithAgents({ author: GAVE_UP_REPLY, onAuthorDispatch: () => (authorDispatches += 1) }),
    );
    await env.EXTRACTION.create({
      id: "wf_a25",
      params: { html: articleHtml, domain: "a25.example.com" },
    });
    const output = await runToTerminal("wf_a25");

    expect(output.state).toBe("error");
    expect(output.error).toMatch(/authoring gave up/);
    expect(authorDispatches).toBe(2);
  });

  it("A26: a dead dynamic worker is a platform failure and ends in error", async () => {
    installWorld(
      worldWithAgents({
        runRecipe: async () => {
          throw new Error("the dynamic worker is unreachable: nothing answers the health probe");
        },
      }),
    );
    await env.EXTRACTION.create({
      id: "wf_a26",
      params: { html: articleHtml, recipe: passingRecipe, domain: "a26.example.com" },
    });
    const output = await runToTerminal("wf_a26");

    expect(output.state).toBe("error");
    expect(output.error).toMatch(/dynamic worker is unreachable/);
  });
});
