import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { readItem } from "../../src/item-store/read-item.ts";
import type { Degradation, Unit } from "../../src/units.ts";
import { insertItem, STALE } from "./insert-item.ts";

beforeEach(async () => {
  await env.DB.prepare("DELETE FROM items").run();
});

describe("readItem", () => {
  it("reads a queued row with no units yet", async () => {
    await insertItem();

    expect(await readItem(env.DB, "itm_0a1b2c3d")).toEqual({
      id: "itm_0a1b2c3d",
      url: "https://example.com/post",
      title: null,
      voice: "af_heart",
      status: "queued",
      created_at: STALE,
      updated_at: STALE,
      queued_at: STALE,
      workflow_instance_id: null,
      current_step: null,
      extraction_domain: null,
      recipe_version_id: null,
      retry_count: 0,
      duration: null,
      audio_format: null,
      units: null,
      degradations: null,
      error: null,
    });
  });

  it("decodes units and degradations stored as JSON", async () => {
    const units: Unit[] = [
      {
        type: "paragraph",
        display: "**Hello** there.",
        spoken: "Hello there.",
        start: 0,
        end: 1.5,
      },
      {
        type: "code",
        display: "```js\nrun()\n```",
        spoken: "Code: a call to run.",
        start: 1.5,
        end: 3,
      },
      {
        type: "image",
        display: "![a chart](/items/itm_0a1b2c3d/images/5f2b)",
        spoken: "Image: a chart.",
        image: "5f2b",
        start: 3,
        end: 4.25,
      },
    ];
    const degradations: Degradation[] = [
      { type: "image", reason: "404", url: "https://example.com/missing.png" },
      { type: "code", reason: "describe failed" },
    ];

    await insertItem({
      status: "ready",
      units: JSON.stringify(units),
      degradations: JSON.stringify(degradations),
    });

    const row = await readItem(env.DB, "itm_0a1b2c3d");

    expect(row?.units).toEqual(units);
    expect(row?.degradations).toEqual(degradations);
  });

  it("answers null for an id with no row", async () => {
    expect(await readItem(env.DB, "itm_ffffffff")).toBeNull();
  });
});
