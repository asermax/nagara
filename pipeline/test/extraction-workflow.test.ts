import { reset } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";
import { scriptReply } from "../src/agents/settlement.ts";
import { articleHtml, failingRecipe, passingRecipe } from "./fixtures/article.ts";
import { readLease, runToTerminal } from "./helpers/http.ts";
import {
  clearWorld,
  type DispatchRecord,
  GAVE_UP_REPLY,
  installWorld,
  NOT_ARTICLE_REPLY,
  worldWithAgents,
} from "./helpers/world.ts";

afterEach(async () => {
  clearWorld();
  await reset();
});

describe("extraction workflow", () => {
  it("a provided recipe that validates outright completes with title and units, no recipe member, and its last step releases the lease", async () => {
    await env.EXTRACTION.create({
      id: "wf_a20",
      params: { html: articleHtml, recipe: passingRecipe, domain: "a20.example.com" },
    });
    const output = await runToTerminal("wf_a20");

    expect(output.state).toBe("complete");
    expect(output.title).toBe("Colorless Green Ideas");
    expect(output.units?.length).toBe(5);
    expect("recipe" in output).toBe(false);
    expect(await readLease("a20.example.com")).toBeUndefined();
  });

  it("a provided recipe that fails validation is revised by the agent and completes carrying the recipe", async () => {
    const dispatches: DispatchRecord[] = [];
    installWorld(worldWithAgents({ revision: scriptReply(passingRecipe), dispatches }));
    await env.EXTRACTION.create({
      id: "wf_a21",
      params: { html: articleHtml, recipe: failingRecipe, domain: "a21.example.com" },
    });
    const output = await runToTerminal("wf_a21");

    expect(dispatches.length).toBeGreaterThan(0);
    expect(dispatches[0].message).toMatch(/Validator report:\n- /);
    expect(output.state).toBe("complete");
    expect(output.recipe).toBe(passingRecipe);
    expect(output.title).toBe("Colorless Green Ideas");
  });

  it("revision exhausting its retries ends in error with the service's string", async () => {
    const dispatches: DispatchRecord[] = [];
    installWorld(worldWithAgents({ revision: GAVE_UP_REPLY, dispatches }));
    await env.EXTRACTION.create({
      id: "wf_a22",
      params: { html: articleHtml, recipe: failingRecipe, domain: "a22.example.com" },
    });
    const output = await runToTerminal("wf_a22");

    expect(output.state).toBe("error");
    expect(output.error).toMatch(/revision gave up/);
    expect(dispatches.filter((d) => d.kind === "revision").length).toBe(3);
  });

  it("an absent recipe authors one, and the settled script runs through the runtime to complete", async () => {
    installWorld(worldWithAgents({ author: scriptReply(passingRecipe) }));
    await env.EXTRACTION.create({
      id: "wf_a23",
      params: { html: articleHtml, domain: "a23.example.com" },
    });
    const output = await runToTerminal("wf_a23");

    expect(output.state).toBe("complete");
    expect(output.recipe).toBe(passingRecipe);
    expect(output.units?.length).toBe(5);
  });

  it("the author's not-article verdict ends the job with nothing saved", async () => {
    installWorld(worldWithAgents({ author: NOT_ARTICLE_REPLY }));
    await env.EXTRACTION.create({
      id: "wf_a24",
      params: { html: articleHtml, domain: "a24.example.com" },
    });
    const output = await runToTerminal("wf_a24");

    expect(output).toEqual({ state: "not_article" });
  });

  it("authoring exhausting its one retry ends in error with the service's string", async () => {
    const dispatches: DispatchRecord[] = [];
    installWorld(worldWithAgents({ author: GAVE_UP_REPLY, dispatches }));
    await env.EXTRACTION.create({
      id: "wf_a25",
      params: { html: articleHtml, domain: "a25.example.com" },
    });
    const output = await runToTerminal("wf_a25");

    expect(output.state).toBe("error");
    expect(output.error).toMatch(/authoring gave up/);
    expect(dispatches.filter((d) => d.kind === "author").length).toBe(2);
  });

  it("a dead dynamic worker is a platform failure and ends in error", async () => {
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
