import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import type { ItemCost } from "../../../src/db/cost-entries/create-cost-entry.ts";
import { database } from "../../../src/db/database.ts";
import { getItem } from "../../../src/db/items/get-item.ts";
import { recordDescriptions } from "../../../src/db/operations/record-descriptions.ts";
import type { CostType } from "../../../src/ledger.ts";
import type { Degradation, Unit } from "../../../src/units.ts";
import { clearTables } from "../clear-tables.ts";
import { ITEM_ID, insertItem } from "../insert-item.ts";
import { costsOf } from "./costs-of.ts";

beforeEach(clearTables);

const UNDESCRIBED: Unit[] = [
  { type: "code", display: "```js\nrun()\n```", spoken: "Code." },
  { type: "image", display: "![a chart](/x)", spoken: "Image: a chart.", image: "5f2b" },
];

const DESCRIBED: Unit[] = [
  { type: "code", display: "```js\nrun()\n```", spoken: "Code: a call to run." },
  { type: "image", display: "![a chart](/x)", spoken: "Image: a chart.", image: "5f2b" },
];

const DEGRADATIONS: Degradation[] = [{ type: "image", reason: "describe failed" }];

const describer = (cached: boolean): ItemCost => ({
  type: "describer",
  quantity: 1,
  unit: "calls",
  dollars: 0.0001,
  cached,
  detail: { kind: "code" },
});

describe("recordDescriptions", () => {
  it("writes the units and degradations and one cost per description, returning the item", async () => {
    const db = database(env.DB);

    await insertItem({ status: "generating", units: UNDESCRIBED });

    const item = await recordDescriptions(
      db,
      ITEM_ID,
      { units: DESCRIBED, degradations: DEGRADATIONS },
      [describer(false), describer(true)],
    );

    expect(item).toEqual(await getItem(db, ITEM_ID));
    expect(item).toMatchObject({ units: DESCRIBED, degradations: DEGRADATIONS });
    expect((await costsOf(ITEM_ID)).map(({ cached }) => cached).sort()).toEqual([false, true]);
  });

  it("writes the units alone when nothing was described", async () => {
    const db = database(env.DB);

    await insertItem({ status: "generating", units: UNDESCRIBED });

    expect(
      await recordDescriptions(db, ITEM_ID, { units: DESCRIBED, degradations: null }, []),
    ).toMatchObject({ units: DESCRIBED, degradations: null });
    expect(await costsOf(ITEM_ID)).toEqual([]);
  });

  it("writes nothing when one cost entry fails", async () => {
    const db = database(env.DB);

    await insertItem({ status: "generating", units: UNDESCRIBED });

    await expect(
      recordDescriptions(db, ITEM_ID, { units: DESCRIBED, degradations: DEGRADATIONS }, [
        describer(false),
        { ...describer(false), type: "bogus" as CostType },
      ]),
    ).rejects.toThrow();
    expect(await getItem(db, ITEM_ID)).toMatchObject({ units: UNDESCRIBED, degradations: null });
    expect(await costsOf(ITEM_ID)).toEqual([]);
  });
});
