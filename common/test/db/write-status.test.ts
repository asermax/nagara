import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { database } from "../../src/db/database.ts";
import { getItem } from "../../src/db/items/get-item.ts";
import { writeStatus } from "../../src/db/items/write-status.ts";
import { clearTables } from "./clear-tables.ts";
import { ITEM_ID, insertItem, STALE } from "./insert-item.ts";

beforeEach(clearTables);

describe("writeStatus", () => {
  it("writes generating for a step and clears the error the row carried", async () => {
    const db = database(env.DB);

    await insertItem({ status: "failed", current_step: "recipe", error: "recipe timed out" });
    await writeStatus(db, ITEM_ID, { status: "generating", currentStep: "lease" });

    const row = await getItem(db, ITEM_ID);

    expect(row).toMatchObject({ status: "generating", current_step: "lease", error: null });
    expect(row?.updated_at).not.toBe(STALE);
    expect(Date.parse(row?.updated_at ?? "")).toBeGreaterThan(Date.parse(STALE));
  });

  it("writes queued with no step and clears the error the row carried", async () => {
    const db = database(env.DB);

    await insertItem({ status: "failed", current_step: "fetch", error: "firecrawl 503" });
    await writeStatus(db, ITEM_ID, { status: "queued", currentStep: null });

    expect(await getItem(db, ITEM_ID)).toMatchObject({
      status: "queued",
      current_step: null,
      error: null,
    });
  });

  it("writes failed with its error and the step it names", async () => {
    const db = database(env.DB);

    await insertItem({ status: "generating", current_step: "store" });
    await writeStatus(db, ITEM_ID, {
      status: "failed",
      currentStep: "store",
      error: "timings do not match the units",
    });

    expect(await getItem(db, ITEM_ID)).toMatchObject({
      status: "failed",
      current_step: "store",
      error: "timings do not match the units",
    });
  });
});
