import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { callApi, type ItemBody } from "./helpers/api.ts";
import { insertItem, readRow } from "./helpers/items.ts";
import { workflowStandIn } from "./helpers/workflow-stand-in.ts";

const failedItem = (fields: Parameters<typeof insertItem>[0] = {}) =>
  insertItem({
    status: "failed",
    current_step: "describe",
    workflow_instance_id: "itm_0a1b2c3d",
    error: "describe timed out",
    ...fields,
  });

beforeEach(async () => {
  await env.DB.prepare("DELETE FROM items").run();
});

describe("POST /items/{id}/retry", () => {
  it("queues a failed item again and restarts its Workflow from the failed step", async () => {
    const id = await failedItem({ retry_count: 1 });
    const { calls, workflow } = workflowStandIn();

    const response = await callApi(`/items/${id}/retry`, { method: "POST", workflow });
    const body = (await response.json()) as ItemBody;
    const row = await readRow(id);

    expect(response.status).toBe(202);
    expect(body).toMatchObject({ status: "queued", error: null });
    expect(row).toMatchObject({ status: "queued", error: null, retry_count: 2 });
    expect(calls.restart).toEqual([
      { instanceId: "itm_0a1b2c3d", options: { from: { name: "describe" } } },
    ]);
  });

  it("restarts an item that failed in recipe from the lease", async () => {
    const id = await failedItem({ current_step: "recipe" });
    const { calls, workflow } = workflowStandIn();

    await callApi(`/items/${id}/retry`, { method: "POST", workflow });

    expect(calls.restart).toEqual([
      { instanceId: "itm_0a1b2c3d", options: { from: { name: "lease" } } },
    ]);
  });

  it("creates the Workflow for an item whose instance was never created", async () => {
    const id = await failedItem({ current_step: null, workflow_instance_id: null });
    const { calls, workflow } = workflowStandIn();

    const response = await callApi(`/items/${id}/retry`, { method: "POST", workflow });

    expect(response.status).toBe(202);
    expect(calls.create).toEqual([{ id, params: { itemId: id } }]);
    expect(calls.restart).toEqual([]);
  });

  it("restarts the instance an item already has when its first step never ran", async () => {
    const id = await failedItem({ current_step: null, workflow_instance_id: null });
    const { calls, workflow } = workflowStandIn({ existingIds: [id] });

    const response = await callApi(`/items/${id}/retry`, { method: "POST", workflow });

    expect(response.status).toBe(202);
    expect(calls.create).toEqual([{ id, params: { itemId: id } }]);
    expect(calls.get).toEqual([id]);
    expect(calls.restart).toEqual([{ instanceId: id, options: undefined }]);
  });

  it("restarts a live instance, since the claim found the item failed", async () => {
    const id = await failedItem();
    const { calls, workflow } = workflowStandIn({ statuses: { itm_0a1b2c3d: "running" } });

    await callApi(`/items/${id}/retry`, { method: "POST", workflow });

    expect(calls.restart).toEqual([
      { instanceId: "itm_0a1b2c3d", options: { from: { name: "describe" } } },
    ]);
  });

  it("restarts the instance the row names, suffix included", async () => {
    const id = await failedItem({ workflow_instance_id: "itm_0a1b2c3d-2" });
    const { calls, workflow } = workflowStandIn();

    await callApi(`/items/${id}/retry`, { method: "POST", workflow });

    expect(calls.get).toEqual(["itm_0a1b2c3d-2"]);
    expect(calls.restart).toEqual([
      { instanceId: "itm_0a1b2c3d-2", options: { from: { name: "describe" } } },
    ]);
  });

  it.each(["errored", "terminated"] as const)(
    "restarts an %s instance that ran a step from current_step rather than replacing it",
    async (status) => {
      const id = await failedItem();
      const { calls, workflow } = workflowStandIn({ statuses: { itm_0a1b2c3d: status } });

      const response = await callApi(`/items/${id}/retry`, { method: "POST", workflow });

      expect(response.status).toBe(202);
      expect(calls.create).toEqual([]);
      expect(calls.restart).toEqual([
        { instanceId: "itm_0a1b2c3d", options: { from: { name: "describe" } } },
      ]);
    },
  );

  it("replaces an errored instance that never ran its first step", async () => {
    const id = await failedItem({ current_step: null, workflow_instance_id: null });
    const { calls, workflow } = workflowStandIn({
      existingIds: [id],
      statuses: { [id]: "errored" },
    });

    const response = await callApi(`/items/${id}/retry`, { method: "POST", workflow });

    expect(response.status).toBe(202);
    expect(calls.create).toEqual([
      { id, params: { itemId: id } },
      { id: `${id}-2`, params: { itemId: id } },
    ]);
    expect(calls.restart).toEqual([]);
    expect((await readRow(id))?.status).toBe("queued");
  });

  it.each([
    { call: "get", standIn: { getError: new Error("(instance.not_found) Instance not found") } },
    {
      call: "restart",
      standIn: { restartError: new Error("(instance.not_found) Instance not found") },
    },
  ])(
    "writes the item back to failed when $call throws, with the retry counted",
    async ({ standIn }) => {
      const id = await failedItem({ retry_count: 1 });
      const { workflow } = workflowStandIn(standIn);

      const response = await callApi(`/items/${id}/retry`, { method: "POST", workflow });
      const body = (await response.json()) as ItemBody;

      expect(response.status).toBe(202);
      expect(body).toMatchObject({
        status: "failed",
        error: "Error: (instance.not_found) Instance not found",
      });
      expect(await readRow(id)).toMatchObject({
        status: "failed",
        current_step: "describe",
        error: "Error: (instance.not_found) Instance not found",
        retry_count: 2,
      });
    },
  );

  it("refuses an item that has used its three retries", async () => {
    const id = await failedItem({ retry_count: 3 });
    const { calls, workflow } = workflowStandIn();

    const response = await callApi(`/items/${id}/retry`, { method: "POST", workflow });

    expect(response.status).toBe(409);
    expect((await readRow(id))?.status).toBe("failed");
    expect(calls).toEqual({ create: [], get: [], restart: [] });
  });

  it("refuses an item that is not failed", async () => {
    const id = await insertItem({ status: "ready", workflow_instance_id: "itm_0a1b2c3d" });
    const { calls, workflow } = workflowStandIn();

    const response = await callApi(`/items/${id}/retry`, { method: "POST", workflow });

    expect(response.status).toBe(409);
    expect(calls).toEqual({ create: [], get: [], restart: [] });
  });

  it("accepts one of two retries sent together and counts it once", async () => {
    const id = await failedItem();
    const { calls, workflow } = workflowStandIn();

    const responses = await Promise.all([
      callApi(`/items/${id}/retry`, { method: "POST", workflow }),
      callApi(`/items/${id}/retry`, { method: "POST", workflow }),
    ]);

    expect(responses.map((response) => response.status).sort()).toEqual([202, 409]);
    expect((await readRow(id))?.retry_count).toBe(1);
    expect(calls.restart).toHaveLength(1);
  });

  it("answers 404 for an unknown id", async () => {
    const response = await callApi("/items/itm_ffffffff/retry", { method: "POST" });

    expect(response.status).toBe(404);
  });
});
