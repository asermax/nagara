import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import type { ItemCost } from "../../../src/db/cost-entries/create-cost-entry.ts";
import { database } from "../../../src/db/database.ts";
import { getItem } from "../../../src/db/items/get-item.ts";
import { recordAudio } from "../../../src/db/operations/record-audio.ts";
import type { CostType } from "../../../src/ledger.ts";
import type { Unit } from "../../../src/units.ts";
import { clearTables } from "../clear-tables.ts";
import { ITEM_ID, insertItem } from "../insert-item.ts";
import { costsOf } from "./costs-of.ts";

beforeEach(clearTables);

const UNTIMED: Unit[] = [{ type: "paragraph", display: "Hello.", spoken: "Hello." }];

const TIMED: Unit[] = [
  { type: "paragraph", display: "Hello.", spoken: "Hello.", start: 0, end: 1.5 },
];

const TTS: ItemCost = {
  type: "tts",
  quantity: 1.5,
  unit: "seconds",
  dollars: 0.002,
  detail: { duration: 1.5 },
};

describe("recordAudio", () => {
  it("turns the item ready with its timed units and audio and records the TTS cost, returning the item", async () => {
    const db = database(env.DB);

    await insertItem({ status: "generating", current_step: "store", units: UNTIMED });

    const item = await recordAudio(
      db,
      ITEM_ID,
      { units: TIMED, duration: 1.5, audio_format: "audio/ogg" },
      TTS,
    );

    expect(item).toEqual(await getItem(db, ITEM_ID));
    expect(item).toMatchObject({
      status: "ready",
      current_step: null,
      error: null,
      units: TIMED,
      duration: 1.5,
      audio_format: "audio/ogg",
    });
    expect(await costsOf(ITEM_ID)).toMatchObject([{ ...TTS, item_id: ITEM_ID }]);
  });

  it("leaves the item generating when the cost entry fails", async () => {
    const db = database(env.DB);

    await insertItem({ status: "generating", current_step: "store", units: UNTIMED });

    await expect(
      recordAudio(
        db,
        ITEM_ID,
        { units: TIMED, duration: 1.5, audio_format: "audio/ogg" },
        { ...TTS, type: "bogus" as CostType },
      ),
    ).rejects.toThrow();
    expect(await getItem(db, ITEM_ID)).toMatchObject({
      status: "generating",
      units: UNTIMED,
      duration: null,
    });
    expect(await costsOf(ITEM_ID)).toEqual([]);
  });
});
