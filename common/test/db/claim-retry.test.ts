import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { database } from "../../src/db/database.ts";
import { claimRetry } from "../../src/db/items/claim-retry.ts";
import { getItem } from "../../src/db/items/get-item.ts";
import { writeStatus } from "../../src/db/items/write-status.ts";
import type { ItemRow } from "../../src/item.ts";
import { clearTables } from "./clear-tables.ts";
import { ITEM_ID, insertItem, STALE } from "./insert-item.ts";

beforeEach(clearTables);

const RETRY_MAX = 3;

const read = async () => (await getItem(database(env.DB), ITEM_ID)) as ItemRow;

describe("claimRetry", () => {
  it("claims a failed item under the cap and returns it queued, error cleared, count raised, queued_at moved", async () => {
    await insertItem({ status: "failed", current_step: "recipe", error: "boom", retry_count: 1 });

    const claimed = await claimRetry(database(env.DB), await read(), RETRY_MAX);

    expect(claimed).toEqual(await read());
    expect(claimed).toMatchObject({ status: "queued", error: null, retry_count: 2 });
    expect(Date.parse(claimed?.queued_at ?? "")).toBeGreaterThan(Date.parse(STALE));
    expect(Date.parse(claimed?.updated_at ?? "")).toBeGreaterThan(Date.parse(STALE));
  });

  it("answers null to a concurrent claim made from the same read", async () => {
    await insertItem({ status: "failed", error: "boom", retry_count: 0 });

    const db = database(env.DB);
    const row = await read();

    expect(await claimRetry(db, row, RETRY_MAX)).not.toBeNull();

    // The winner's restart failed and wrote failed again, so only the count it raised keeps the
    // loser from claiming a second time.
    await writeStatus(db, ITEM_ID, {
      status: "failed",
      currentStep: null,
      error: "restart failed",
    });

    expect(await claimRetry(db, row, RETRY_MAX)).toBeNull();
    expect(await read()).toMatchObject({ status: "failed", retry_count: 1 });
  });

  it("refuses an item at the cap with null", async () => {
    await insertItem({ status: "failed", error: "boom", retry_count: RETRY_MAX });

    expect(await claimRetry(database(env.DB), await read(), RETRY_MAX)).toBeNull();
    expect(await read()).toMatchObject({ status: "failed", retry_count: RETRY_MAX });
  });

  it("refuses an item that is not failed with null", async () => {
    await insertItem({ status: "generating", current_step: "images" });

    expect(await claimRetry(database(env.DB), await read(), RETRY_MAX)).toBeNull();
    expect(await read()).toMatchObject({ status: "generating", retry_count: 0 });
  });
});
