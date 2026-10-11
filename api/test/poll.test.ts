import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { callApi } from "./helpers/api.ts";
import { insertItem, minutesAgo, readRow } from "./helpers/items.ts";
import { workflowStandIn } from "./helpers/workflow-stand-in.ts";

const timedUnits = [
  { type: "paragraph", display: "Hello **world**.", spoken: "Hello world.", start: 0, end: 1.5 },
  { type: "code", display: "```py\nx = 1\n```", spoken: "Code: sets x.", start: 1.5, end: 3 },
  {
    type: "image",
    display: "![a chart](/items/itm_0a1b2c3d/images/abc123)",
    spoken: "Image: a chart.",
    image: "abc123",
    start: 3,
    end: 4.25,
  },
];

const untimedUnits = timedUnits.map(({ start: _start, end: _end, ...unit }) => unit);

beforeEach(async () => {
  await env.DB.prepare("DELETE FROM items").run();
});

describe("GET /items/{id}", () => {
  it("returns a ready item's timed units without their spoken form, its audio url and duration", async () => {
    const id = await insertItem({
      status: "ready",
      title: "A post",
      workflow_instance_id: "wf-1",
      duration: 4.25,
      audio_format: "audio/ogg",
      units: JSON.stringify(timedUnits),
    });

    const response = await callApi(`/items/${id}`);

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      id,
      url: "https://example.com/post",
      title: "A post",
      status: "ready",
      voice: "af_heart",
      created_at: expect.any(String),
      duration: 4.25,
      units: [
        { index: 0, type: "paragraph", display: "Hello **world**.", start: 0, end: 1.5 },
        { index: 1, type: "code", display: "```py\nx = 1\n```", start: 1.5, end: 3 },
        {
          index: 2,
          type: "image",
          display: "![a chart](/items/itm_0a1b2c3d/images/abc123)",
          image: "abc123",
          start: 3,
          end: 4.25,
        },
      ],
      error: null,
      audio_url: `/items/${id}/audio`,
    });
  });

  it("holds a generating item's units back and gives it no audio url", async () => {
    const id = await insertItem({
      status: "generating",
      current_step: "describe",
      workflow_instance_id: "wf-1",
      units: JSON.stringify(untimedUnits),
    });

    const body = await (await callApi(`/items/${id}`)).json();

    expect(body).toMatchObject({ status: "generating", units: null, audio_url: null });
  });

  it("returns a failed item with its error", async () => {
    const id = await insertItem({
      status: "failed",
      current_step: "fetch",
      workflow_instance_id: "wf-1",
      error: "firecrawl answered 503",
    });

    const body = await (await callApi(`/items/${id}`)).json();

    expect(body).toMatchObject({ status: "failed", error: "firecrawl answered 503", units: null });
  });

  it("restarts a stale queued item from its restart point without counting a retry", async () => {
    const stale = minutesAgo(16);
    const id = await insertItem({
      queued_at: stale,
      current_step: "recipe",
      workflow_instance_id: "wf-1",
      retry_count: 1,
    });
    const { calls, workflow } = workflowStandIn();

    const response = await callApi(`/items/${id}`, { workflow });
    const row = await readRow(id);

    expect(response.status).toBe(200);
    expect(calls.get).toEqual(["wf-1"]);
    expect(calls.restart).toEqual([{ instanceId: "wf-1", options: { from: { name: "lease" } } }]);
    expect(calls.create).toEqual([]);
    expect(row?.queued_at).not.toBe(stale);
    expect(row?.retry_count).toBe(1);
    expect(row?.status).toBe("queued");
  });

  it("creates the Workflow for a stale queued item whose instance never ran", async () => {
    const id = await insertItem({ queued_at: minutesAgo(16) });
    const { calls, workflow } = workflowStandIn();

    await callApi(`/items/${id}`, { workflow });

    expect(calls.create).toEqual([{ params: { itemId: id } }]);
    expect(calls.restart).toEqual([]);
  });

  it("restarts a stale queued item once when two polls arrive together", async () => {
    const id = await insertItem({
      queued_at: minutesAgo(16),
      current_step: "fetch",
      workflow_instance_id: "wf-1",
    });
    const { calls, workflow } = workflowStandIn();

    const responses = await Promise.all([
      callApi(`/items/${id}`, { workflow }),
      callApi(`/items/${id}`, { workflow }),
    ]);

    expect(responses.map((response) => response.status)).toEqual([200, 200]);
    expect(calls.restart).toEqual([{ instanceId: "wf-1", options: { from: { name: "fetch" } } }]);
  });

  it("leaves a queued item two minutes old alone", async () => {
    const queuedAt = minutesAgo(2);
    const id = await insertItem({ queued_at: queuedAt, workflow_instance_id: "wf-1" });
    const { calls, workflow } = workflowStandIn();

    await callApi(`/items/${id}`, { workflow });

    expect(calls).toEqual({ create: [], get: [], restart: [] });
    expect((await readRow(id))?.queued_at).toBe(queuedAt);
  });

  it("answers 404 for an unknown id", async () => {
    const response = await callApi("/items/itm_ffffffff");

    expect(response.status).toBe(404);
  });
});
