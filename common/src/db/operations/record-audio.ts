import { eq } from "drizzle-orm";
import { ITEM_STATUS } from "../../item.ts";
import type { ItemCost } from "../cost-entries/create-cost-entry.ts";
import type { Database } from "../database.ts";
import type { ItemChanges } from "../items/update-item.ts";
import { costEntries, items } from "../schema.ts";

type Synthesized = Required<Pick<ItemChanges, "units" | "duration" | "audio_format">>;

export const recordAudio = async (
  db: Database,
  itemId: string,
  synthesized: Synthesized,
  cost: ItemCost,
) => {
  const [[item]] = await db.batch([
    db
      .update(items)
      .set({ ...synthesized, status: ITEM_STATUS.ready, current_step: null, error: null })
      .where(eq(items.id, itemId))
      .returning(),
    db.insert(costEntries).values({ ...cost, item_id: itemId }),
  ]);

  return item ?? null;
};
