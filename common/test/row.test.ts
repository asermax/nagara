import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import type { ItemRow } from "../src/item.ts";
import { readItem, writeStatus } from "../src/row.ts";
import type { Degradation, Unit } from "../src/units.ts";

const STALE = "2026-01-01T00:00:00.000Z";

const insertItem = async (fields: Partial<Record<keyof ItemRow, string | number | null>> = {}) => {
  const row = {
    id: "itm_0a1b2c3d",
    url: "https://example.com/post",
    voice: "af_heart",
    status: "queued",
    created_at: STALE,
    updated_at: STALE,
    queued_at: STALE,
    ...fields,
  };
  const columns = Object.keys(row);

  await env.DB.prepare(
    `INSERT INTO items (${columns.join(", ")}) VALUES (${columns.map(() => "?").join(", ")})`,
  )
    .bind(...Object.values(row))
    .run();
};

beforeEach(async () => {
  await env.DB.prepare("DELETE FROM items").run();
});

describe("writeStatus", () => {
  it("writes generating for a step and clears the error the row carried", async () => {
    await insertItem({ status: "failed", current_step: "recipe", error: "recipe timed out" });

    await writeStatus(env.DB, "itm_0a1b2c3d", { status: "generating", currentStep: "lease" });

    const row = await readItem(env.DB, "itm_0a1b2c3d");

    expect(row).toMatchObject({ status: "generating", current_step: "lease", error: null });
    expect(row?.updated_at).not.toBe(STALE);
    expect(Date.parse(row?.updated_at ?? "")).toBeGreaterThan(Date.parse(STALE));
  });

  it("writes queued with no step and clears the error the row carried", async () => {
    await insertItem({ status: "failed", current_step: "fetch", error: "firecrawl 503" });

    await writeStatus(env.DB, "itm_0a1b2c3d", { status: "queued", currentStep: null });

    expect(await readItem(env.DB, "itm_0a1b2c3d")).toMatchObject({
      status: "queued",
      current_step: null,
      error: null,
    });
  });

  it("writes failed with its error and the step it names", async () => {
    await insertItem({ status: "generating", current_step: "store" });

    await writeStatus(env.DB, "itm_0a1b2c3d", {
      status: "failed",
      currentStep: "store",
      error: "timings do not match the units",
    });

    expect(await readItem(env.DB, "itm_0a1b2c3d")).toMatchObject({
      status: "failed",
      current_step: "store",
      error: "timings do not match the units",
    });
  });
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
