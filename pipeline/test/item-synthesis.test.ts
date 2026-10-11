import { env } from "cloudflare:workers";
import { describe, expect, it } from "vitest";
import { instanceIdOf, readRow, runItem } from "./helpers/item.ts";
import { logStatuses, scenario, statusesOf } from "./helpers/scenario.ts";
import { modal, requests, server, useServer } from "./helpers/services.ts";

useServer();

describe("synthesis", () => {
  it("fails in start synthesis when Modal answers 503 on every attempt", async () => {
    const { synthesis } = await scenario({
      itemId: "itm_00000c15",
      domain: "c15.test",
      modal: { start: 503 },
    });

    await runItem("itm_00000c15", "errored");

    expect(await readRow("itm_00000c15")).toMatchObject({
      status: "failed",
      current_step: "start synthesis",
      error: "modal start answered 503",
    });
    expect(synthesis.calls.starts).toHaveLength(3);
  });

  it("fails in wait for synthesis when the result answers 500 on every attempt", async () => {
    const { synthesis } = await scenario({
      itemId: "itm_00000c16",
      domain: "c16.test",
      modal: { results: [500] },
    });

    await runItem("itm_00000c16", "errored");

    expect(await readRow("itm_00000c16")).toMatchObject({
      status: "failed",
      current_step: "wait for synthesis",
      error: "modal result answered 500",
    });
    expect(synthesis.calls.results).toBe(3);
  });

  it("fails at once in wait for synthesis when the result has expired", async () => {
    const { synthesis } = await scenario({
      itemId: "itm_00000c17",
      domain: "c17.test",
      modal: { results: ["running", 410] },
    });

    await runItem("itm_00000c17", "errored");

    expect(await readRow("itm_00000c17")).toMatchObject({
      status: "failed",
      current_step: "wait for synthesis",
      error: "modal result answered 410",
    });
    expect(synthesis.calls.results).toBe(2);
  });

  it("fails at once in store when the synthesis returns one window fewer than the units", async () => {
    await scenario({ itemId: "itm_00000c18", domain: "c18.test", modal: { results: ["short"] } });

    await runItem("itm_00000c18", "errored");

    const row = await readRow("itm_00000c18");

    expect(row).toMatchObject({
      status: "failed",
      current_step: "store",
      error: "the synthesis returned 2 timing windows for 3 units",
    });
    expect(row.units?.every((unit) => unit.start == null)).toBe(true);
  });

  it("restarts a failed wait for synthesis without fetching, describing or synthesizing again", async () => {
    await logStatuses();

    const itemId = "itm_00000c19";
    const { synthesis } = await scenario({ itemId, domain: "c19.test", modal: { results: [500] } });
    const instance = await runItem(itemId, "errored");

    expect((await readRow(itemId)).current_step).toBe("wait for synthesis");

    const recovered = modal({ results: ["ready"], paragraphs: 3 });

    requests.length = 0;
    server.use(...recovered.handlers);

    await (await env.ITEM_WORKFLOW.get(instanceIdOf(itemId))).restart({
      from: { name: "wait for synthesis" },
    });
    await instance.waitForStatus("complete");

    const statuses = await statusesOf(itemId);

    expect(statuses.slice(statuses.lastIndexOf("failed wait for synthesis") + 1)).toEqual([
      "generating wait for synthesis",
      "generating store",
      "ready",
    ]);
    expect(await readRow(itemId)).toMatchObject({ status: "ready", error: null, duration: 3 });
    expect(requests).toEqual([
      expect.stringMatching(/^GET https:\/\/modal\.test\/result\?call_id=fc-01TEST$/),
    ]);
    expect(synthesis.calls.starts).toHaveLength(1);
  });
});
