import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { database } from "../../src/db/database.ts";
import { getItem } from "../../src/db/items/get-item.ts";
import { updateItem } from "../../src/db/items/update-item.ts";
import { clearTables } from "./clear-tables.ts";
import { ITEM_ID, insertItem, STALE } from "./insert-item.ts";

beforeEach(clearTables);

describe("updateItem", () => {
  it("writes the given columns, sets updated_at and leaves the others alone", async () => {
    const db = database(env.DB);

    await insertItem({ title: "Before" });
    await updateItem(db, ITEM_ID, { extraction_domain: "example.com" });

    const row = await getItem(db, ITEM_ID);

    expect(row).toMatchObject({
      extraction_domain: "example.com",
      title: "Before",
      created_at: STALE,
      queued_at: STALE,
    });
    expect(Date.parse(row?.updated_at ?? "")).toBeGreaterThan(Date.parse(STALE));
  });
});
