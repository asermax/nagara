import { env } from "cloudflare:workers";
import { database, getItem, items } from "@nagara/common";

type Fields = Partial<typeof items.$inferInsert>;

export const minutesAgo = (minutes: number) =>
  new Date(Date.now() - minutes * 60_000).toISOString();

export const insertItem = async ({ id = "itm_0a1b2c3d", ...fields }: Fields = {}) => {
  await database(env.DB)
    .insert(items)
    .values({
      id,
      url: "https://example.com/post",
      voice: "af_heart",
      status: "queued",
      created_at: minutesAgo(1),
      updated_at: minutesAgo(1),
      queued_at: minutesAgo(1),
      ...fields,
    });

  return id;
};

export const clearItems = () => database(env.DB).delete(items);

export const countItems = () => database(env.DB).$count(items);

export const readRow = (id: string) => getItem(database(env.DB), id);
