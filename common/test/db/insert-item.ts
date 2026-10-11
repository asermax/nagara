import { env } from "cloudflare:workers";
import { database } from "../../src/db/database.ts";
import { items } from "../../src/db/schema.ts";

export const STALE = "2026-01-01T00:00:00.000Z";

export const ITEM_ID = "itm_0a1b2c3d";

export const insertItem = (fields: Partial<typeof items.$inferInsert> = {}) =>
  database(env.DB)
    .insert(items)
    .values({
      id: ITEM_ID,
      url: "https://example.com/post",
      voice: "af_heart",
      status: "queued",
      created_at: STALE,
      updated_at: STALE,
      queued_at: STALE,
      ...fields,
    });
