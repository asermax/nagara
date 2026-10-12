import { eq } from "drizzle-orm";
import type { ItemCost } from "../cost-entries/create-cost-entry.ts";
import type { Database } from "../database.ts";
import type { ItemChanges } from "../items/update-item.ts";
import { costEntries, items } from "../schema.ts";

type Fetched = Required<Pick<ItemChanges, "workflow_instance_id" | "extraction_domain">>;

export const recordFetch = async (
  db: Database,
  itemId: string,
  fetched: Fetched,
  cost: ItemCost,
) => {
  const [[item]] = await db.batch([
    db.update(items).set(fetched).where(eq(items.id, itemId)).returning(),
    db.insert(costEntries).values({ ...cost, item_id: itemId }),
  ]);

  return item ?? null;
};
