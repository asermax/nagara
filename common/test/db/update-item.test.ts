import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { database } from "../../src/db/database.ts";
import { getItem } from "../../src/db/items/get-item.ts";
import { updateItem } from "../../src/db/items/update-item.ts";
import { clearTables } from "./clear-tables.ts";
import { ITEM_ID, insertItem, STALE } from "./insert-item.ts";

beforeEach(clearTables);

describe("updateItem", () => {
  it("writes the given columns, sets updated_at, leaves the others alone and returns the row", async () => {
    const db = database(env.DB);

    await insertItem({ title: "Before" });
    const row = await updateItem(db, ITEM_ID, { extraction_domain: "example.com" });

    expect(row).toEqual(await getItem(db, ITEM_ID));

    expect(row).toMatchObject({
      extraction_domain: "example.com",
      title: "Before",
      created_at: STALE,
      queued_at: STALE,
    });
    expect(Date.parse(row?.updated_at ?? "")).toBeGreaterThan(Date.parse(STALE));
  });

  it("answers null for an id with no row", async () => {
    expect(await updateItem(database(env.DB), "itm_ffffffff", { title: "None" })).toBeNull();
  });
});
