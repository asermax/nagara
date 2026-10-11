import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { callApi } from "./helpers/api.ts";
import { readRow } from "./helpers/items.ts";
import { workflowStandIn } from "./helpers/workflow-stand-in.ts";

const VOICE_POOL = [
  "af_heart",
  "af_bella",
  "af_sarah",
  "af_sky",
  "af_aoede",
  "af_alloy",
  "af_nova",
  "am_fenrir",
  "am_michael",
  "am_puck",
];

type ItemBody = { id: string; status: string; voice: string; error: string | null };

beforeEach(async () => {
  await env.DB.prepare("DELETE FROM items").run();
});

describe("POST /items", () => {
  it("writes a queued row with the requested voice and creates the item's Workflow", async () => {
    const { calls, workflow } = workflowStandIn();

    const response = await callApi("/items", {
      method: "POST",
      body: { url: "https://example.com/post", voice: "bf_emma" },
      workflow,
    });
    const body = (await response.json()) as ItemBody;
    const row = await readRow(body.id);

    expect(response.status).toBe(202);
    expect(body).toMatchObject({ status: "queued", voice: "bf_emma", error: null });
    expect(body.id).toMatch(/^itm_[0-9a-f]{8}$/);

    expect(row).toMatchObject({
      url: "https://example.com/post",
      voice: "bf_emma",
      status: "queued",
      retry_count: 0,
    });
    expect(row?.queued_at).toEqual(expect.any(String));

    expect(calls.create).toEqual([{ params: { itemId: body.id } }]);
  });

  it("picks a voice from the curated pool when the request names none", async () => {
    const response = await callApi("/items", {
      method: "POST",
      body: { url: "https://example.com/post" },
    });
    const body = (await response.json()) as ItemBody;

    expect(response.status).toBe(202);
    expect(VOICE_POOL).toContain(body.voice);
    expect((await readRow(body.id))?.voice).toBe(body.voice);
  });

  it("refuses a body with no url and writes no row", async () => {
    const { calls, workflow } = workflowStandIn();

    const response = await callApi("/items", {
      method: "POST",
      body: { voice: "af_heart" },
      workflow,
    });
    const count = await env.DB.prepare("SELECT COUNT(*) AS n FROM items").first<{ n: number }>();

    expect(response.status).toBe(400);
    expect(count?.n).toBe(0);
    expect(calls.create).toEqual([]);
  });

  it("returns the item failed with the create's error when the Workflow cannot be created", async () => {
    const { workflow } = workflowStandIn({
      createError: new Error("(workflow.not_found) Workflow does not exist"),
    });

    const response = await callApi("/items", {
      method: "POST",
      body: { url: "https://example.com/post" },
      workflow,
    });
    const body = (await response.json()) as ItemBody;
    const row = await readRow(body.id);

    expect(response.status).toBe(202);
    expect(body.status).toBe("failed");
    expect(body.error).toContain("(workflow.not_found) Workflow does not exist");
    expect(row).toMatchObject({ status: "failed", current_step: null, error: body.error });
  });
});
