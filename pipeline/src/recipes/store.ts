import type { RecipeVersionRow } from "@nagara/common";

// The recipe key: the host of the fetch's final URL with only a leading www dropped, so subdomains
// stay distinct domains and consolidation comes from redirects alone.
export const domainFromUrl = (url: string) => new URL(url).hostname.replace(/^www\./, "");

export const currentRecipe = (db: D1Database, domain: string) =>
  db
    .prepare("SELECT * FROM recipe_versions WHERE domain = ? ORDER BY version DESC LIMIT 1")
    .bind(domain)
    .first<RecipeVersionRow>();

// A revision is a pure insert at the next version; the unique (domain, version) pair turns two
// concurrent saves into one failure rather than two rows with one number.
export const saveVersion = async (db: D1Database, domain: string, script: string) => {
  const id = `rcp_${crypto.randomUUID().replaceAll("-", "").slice(0, 8)}`;

  await db
    .prepare(
      `INSERT INTO recipe_versions (id, domain, version, script, created_at)
       SELECT ?, ?, COALESCE(MAX(version), 0) + 1, ?, ? FROM recipe_versions WHERE domain = ?`,
    )
    .bind(id, domain, script, new Date().toISOString(), domain)
    .run();

  return id;
};
