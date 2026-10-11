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
  it("claims a queued item queued before the cutoff and returns it with queued_at moved", async () => {
    const db = database(env.DB);

    await insertItem();

    const claimed = await claimRequeue(db, ITEM_ID, STALE_BEFORE);

    expect(claimed).toEqual(await getItem(db, ITEM_ID));
    expect(claimed).toMatchObject({ status: "queued", retry_count: 0 });
    expect(Date.parse(claimed?.queued_at ?? "")).toBeGreaterThan(Date.parse(STALE));
    expect(Date.parse(claimed?.updated_at ?? "")).toBeGreaterThan(Date.parse(STALE));
  });

  it("answers null for an item queued after the cutoff", async () => {
    const db = database(env.DB);

    await insertItem({ queued_at: "2026-01-01T00:20:00.000Z" });

    expect(await claimRequeue(db, ITEM_ID, STALE_BEFORE)).toBeNull();
    expect((await getItem(db, ITEM_ID))?.queued_at).toBe("2026-01-01T00:20:00.000Z");
  });

  it("answers null to a second claim once the first moved queued_at", async () => {
    const db = database(env.DB);

    await insertItem();

    expect(await claimRequeue(db, ITEM_ID, STALE_BEFORE)).not.toBeNull();
    expect(await claimRequeue(db, ITEM_ID, STALE_BEFORE)).toBeNull();
  });
});
