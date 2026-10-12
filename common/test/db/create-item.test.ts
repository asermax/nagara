import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { database } from "../../src/db/database.ts";
import { createItem } from "../../src/db/items/create-item.ts";
import { getItem } from "../../src/db/items/get-item.ts";
import { clearTables } from "./clear-tables.ts";

beforeEach(clearTables);

describe("createItem", () => {
  it("inserts a queued item under a minted id with its timestamps and returns it", async () => {
    const db = database(env.DB);
    const before = Date.now();

    const item = await createItem(db, { url: "https://example.com/post", voice: "af_heart" });

    expect(item).toMatchObject({
      url: "https://example.com/post",
      voice: "af_heart",
      status: "queued",
      retry_count: 0,
      workflow_instance_id: null,
      error: null,
    });
    expect(item.id).toMatch(/^itm_[0-9a-f]{8}$/);

    for (const stamp of [item.created_at, item.updated_at, item.queued_at]) {
      expect(Date.parse(stamp)).toBeGreaterThanOrEqual(before);
    }

    expect(await getItem(db, item.id)).toEqual(item);
  });
});
