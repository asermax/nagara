import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { readItem } from "../../src/item-store/read-item.ts";
import { writeStatus } from "../../src/item-store/write-status.ts";
import { insertItem, STALE } from "./insert-item.ts";

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
