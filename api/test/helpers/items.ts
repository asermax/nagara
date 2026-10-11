import { env } from "cloudflare:workers";
import type { ItemRow } from "@nagara/common";

type Fields = Partial<Record<Exclude<keyof ItemRow, "id">, string | number | null>> & {
  id?: string;
};

export const minutesAgo = (minutes: number) =>
  new Date(Date.now() - minutes * 60_000).toISOString();

export const insertItem = async ({ id = "itm_0a1b2c3d", ...fields }: Fields = {}) => {
  const row = {
    id,
    url: "https://example.com/post",
    voice: "af_heart",
    status: "queued",
    created_at: minutesAgo(1),
    updated_at: minutesAgo(1),
    queued_at: minutesAgo(1),
    ...fields,
  };
  const columns = Object.keys(row);

  await env.DB.prepare(
    `INSERT INTO items (${columns.join(", ")}) VALUES (${columns.map(() => "?").join(", ")})`,
  )
    .bind(...Object.values(row))
    .run();

  return id;
};

export const readRow = (id: string) =>
  env.DB.prepare("SELECT * FROM items WHERE id = ?").bind(id).first<Record<string, unknown>>();
