import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { createCostEntry } from "../../src/db/cost-entries/create-cost-entry.ts";
import { database } from "../../src/db/database.ts";
import { clearTables } from "./clear-tables.ts";
import { ITEM_ID, insertItem } from "./insert-item.ts";

beforeEach(clearTables);

describe("createCostEntry", () => {
  it("inserts an entry under a minted id, uncached unless told, and returns it", async () => {
    await insertItem();

    const entry = await createCostEntry(database(env.DB), {
      item_id: ITEM_ID,
      type: "tts",
      quantity: 12.5,
      unit: "seconds",
      dollars: 0.01,
      detail: { duration: 12.5 },
    });

    expect(entry).toMatchObject({
      item_id: ITEM_ID,
      type: "tts",
      quantity: 12.5,
      cached: false,
      detail: { duration: 12.5 },
    });
    expect(entry.id).toMatch(/^cst_[0-9a-f]{12}$/);
    expect(Number.isNaN(Date.parse(entry.created_at))).toBe(false);
  });
});
