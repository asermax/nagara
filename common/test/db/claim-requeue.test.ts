import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { database } from "../../src/db/database.ts";
import { claimRequeue } from "../../src/db/items/claim-requeue.ts";
import { getItem } from "../../src/db/items/get-item.ts";
import { clearTables } from "./clear-tables.ts";
import { ITEM_ID, insertItem, STALE } from "./insert-item.ts";

beforeEach(clearTables);

const STALE_BEFORE = "2026-01-01T00:15:00.000Z";

describe("claimRequeue", () => {
  it("claims a queued item queued before the cutoff and moves its queued_at", async () => {
    const db = database(env.DB);

    await insertItem();

    expect(await claimRequeue(db, ITEM_ID, STALE_BEFORE)).toBe(true);

    const row = await getItem(db, ITEM_ID);

    expect(row).toMatchObject({ status: "queued", retry_count: 0 });
    expect(row?.queued_at).not.toBe(STALE);
    expect(row?.updated_at).toBe(row?.queued_at);
  });

  it("refuses an item queued after the cutoff", async () => {
    const db = database(env.DB);

    await insertItem({ queued_at: "2026-01-01T00:20:00.000Z" });

    expect(await claimRequeue(db, ITEM_ID, STALE_BEFORE)).toBe(false);
    expect((await getItem(db, ITEM_ID))?.queued_at).toBe("2026-01-01T00:20:00.000Z");
  });

  it("refuses a second claim once the first moved queued_at", async () => {
    const db = database(env.DB);

    await insertItem();

    expect(await claimRequeue(db, ITEM_ID, STALE_BEFORE)).toBe(true);
    expect(await claimRequeue(db, ITEM_ID, STALE_BEFORE)).toBe(false);
  });
});
