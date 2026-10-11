import { env } from "cloudflare:workers";
import type { RequestHandler } from "msw";
import { saveVersion } from "../../src/recipes/store.ts";
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

  const recipeVersionId = recipe == null ? null : await saveVersion(env.DB, domain, recipe);

  await insertItem(itemId, url);
  server.use(
    ...handlers,
    ...synthesis.handlers,
    ...replay(firecrawlCassette(url, firecrawl ?? [firecrawlPage(html, url)]), ...cassettes),
  );

  return { url, synthesis, recipeVersionId };
};

// Every write to an item's status lands here, so a test can read the sequence a run went through.
export const logStatuses = async () => {
  await env.DB.batch([
    env.DB.prepare(
      "CREATE TABLE IF NOT EXISTS status_log (seq INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, status TEXT, current_step TEXT)",
    ),
    env.DB.prepare(
      `CREATE TRIGGER IF NOT EXISTS log_status AFTER UPDATE OF status, current_step ON items
       BEGIN INSERT INTO status_log (item_id, status, current_step) VALUES (NEW.id, NEW.status, NEW.current_step); END`,
    ),
  ]);
};

export const statusesOf = async (itemId: string) =>
  (
    await env.DB.prepare(
      "SELECT status, current_step FROM status_log WHERE item_id = ? ORDER BY seq",
    )
      .bind(itemId)
      .all<{ status: string; current_step: string | null }>()
  ).results.map(({ status, current_step }) => `${status} ${current_step ?? ""}`.trim());
