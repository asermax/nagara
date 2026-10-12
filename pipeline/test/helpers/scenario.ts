import { env } from "cloudflare:workers";
import { createRecipeVersion, database } from "@nagara/common";
import { asc, eq, sql } from "drizzle-orm";
import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";
import type { RequestHandler } from "msw";
import { articleHtml, articleRecipe } from "../fixtures/item-article.ts";
import { insertItem } from "./item.ts";
import {
  codeDescribe,
  firecrawlCassette,
  firecrawlPage,
  type ModalScript,
  modal,
  replay,
  server,
} from "./services.ts";

export type Scenario = {
  itemId: string;
  domain: string;
  html?: string;
  recipe?: string | null;
  firecrawl?: { status: number; body: unknown }[];
  cassettes?: string[];
  modal?: ModalScript;
  handlers?: RequestHandler[];
};

// One item and the services it reaches: its recipe saved for its domain, Firecrawl and the code
// describe replayed from cassettes, Modal and anything in `handlers` answered in front of them.
export const scenario = async ({
  itemId,
  domain,
  html = articleHtml(),
  recipe = articleRecipe,
  firecrawl,
  cassettes = [codeDescribe],
  modal: modalScript,
  handlers = [],
}: Scenario) => {
  const url = `https://${domain}/${itemId}`;
  const synthesis = modal(modalScript);

  const recipeVersionId =
    recipe == null
      ? null
      : (await createRecipeVersion(database(env.DB), { domain, script: recipe })).id;

  await insertItem(itemId, url);
  server.use(
    ...handlers,
    ...synthesis.handlers,
    ...replay(firecrawlCassette(url, firecrawl ?? [firecrawlPage(html, url)]), ...cassettes),
  );

  return { url, synthesis, recipeVersionId };
};

export const statusLog = sqliteTable("status_log", {
  seq: integer().primaryKey({ autoIncrement: true }),
  item_id: text(),
  status: text(),
  current_step: text(),
});

// Every write to an item's status lands here, so a test can read the sequence a run went through.
// The table and its trigger exist only in these tests, so they are created here rather than in a
// migration.
export const logStatuses = async () => {
  const db = database(env.DB);

  await db.batch([
    db.run(
      sql`CREATE TABLE IF NOT EXISTS status_log (seq INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, status TEXT, current_step TEXT)`,
    ),
    db.run(
      sql`CREATE TRIGGER IF NOT EXISTS log_status AFTER UPDATE OF status, current_step ON items
       BEGIN INSERT INTO status_log (item_id, status, current_step) VALUES (NEW.id, NEW.status, NEW.current_step); END`,
    ),
  ]);
};

export const statusesOf = async (itemId: string) =>
  (
    await database(env.DB)
      .select({ status: statusLog.status, current_step: statusLog.current_step })
      .from(statusLog)
      .where(eq(statusLog.item_id, itemId))
      .orderBy(asc(statusLog.seq))
  ).map(({ status, current_step }) => `${status} ${current_step ?? ""}`.trim());
