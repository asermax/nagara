import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import type { ItemCost } from "../../../src/db/cost-entries/create-cost-entry.ts";
import { database } from "../../../src/db/database.ts";
import { getItem } from "../../../src/db/items/get-item.ts";
import { recordFetch } from "../../../src/db/operations/record-fetch.ts";
import type { CostType } from "../../../src/ledger.ts";
import { clearTables } from "../clear-tables.ts";
import { ITEM_ID, insertItem } from "../insert-item.ts";
import { costsOf } from "./costs-of.ts";

beforeEach(clearTables);

const FIRECRAWL: ItemCost = {
  type: "firecrawl",
  quantity: 1,
  unit: "credits",
  dollars: 0.001,
  detail: { destination: "https://example.com/post", proxy: "basic" },
};

describe("recordFetch", () => {
  it("names the instance and the domain and records the Firecrawl cost, returning the item", async () => {
    const db = database(env.DB);

    await insertItem();

    const item = await recordFetch(
      db,
      ITEM_ID,
      { workflow_instance_id: "wf-1", extraction_domain: "example.com" },
      FIRECRAWL,
    );

    expect(item).toEqual(await getItem(db, ITEM_ID));
    expect(item).toMatchObject({ workflow_instance_id: "wf-1", extraction_domain: "example.com" });
    expect(await costsOf(ITEM_ID)).toMatchObject([{ ...FIRECRAWL, item_id: ITEM_ID }]);
  });

  it("writes neither when the cost entry fails", async () => {
    const db = database(env.DB);

    await insertItem();

    await expect(
      recordFetch(
        db,
        ITEM_ID,
        { workflow_instance_id: "wf-1", extraction_domain: "example.com" },
        { ...FIRECRAWL, type: "bogus" as CostType },
      ),
    ).rejects.toThrow();
    expect(await getItem(db, ITEM_ID)).toMatchObject({
      workflow_instance_id: null,
      extraction_domain: null,
    });
    expect(await costsOf(ITEM_ID)).toEqual([]);
  });
});
