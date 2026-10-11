import { env } from "cloudflare:workers";
import type { ItemRow } from "../../src/item.ts";

export const STALE = "2026-01-01T00:00:00.000Z";

export const insertItem = async (
  fields: Partial<Record<keyof ItemRow, string | number | null>> = {},
) => {
  const row = {
    id: "itm_0a1b2c3d",
    url: "https://example.com/post",
    voice: "af_heart",
    status: "queued",
    created_at: STALE,
    updated_at: STALE,
    queued_at: STALE,
    ...fields,
  };
  const columns = Object.keys(row);

  await env.DB.prepare(
    `INSERT INTO items (${columns.join(", ")}) VALUES (${columns.map(() => "?").join(", ")})`,
  )
    .bind(...Object.values(row))
    .run();
};
