import { eq } from "drizzle-orm";
import type { ItemCost } from "../cost-entries/create-cost-entry.ts";
import type { Database } from "../database.ts";
import type { ItemChanges } from "../items/update-item.ts";
import { costEntries, items } from "../schema.ts";

type Described = Required<Pick<ItemChanges, "units" | "degradations">>;

export const recordDescriptions = async (
  db: Database,
  itemId: string,
  described: Described,
  costs: ItemCost[],
) => {
  const [[item]] = await db.batch([
    db.update(items).set(described).where(eq(items.id, itemId)).returning(),
    ...costs.map((cost) => db.insert(costEntries).values({ ...cost, item_id: itemId })),
  ]);

  return item ?? null;
};
