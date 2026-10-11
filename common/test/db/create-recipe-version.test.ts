import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { database } from "../../src/db/database.ts";
import { createRecipeVersion } from "../../src/db/recipe-versions/create-recipe-version.ts";
import { getLatestRecipeVersion } from "../../src/db/recipe-versions/get-latest-recipe-version.ts";
import { clearTables } from "./clear-tables.ts";

beforeEach(clearTables);

describe("createRecipeVersion", () => {
  it("saves a domain's first script as version 1", async () => {
    const db = database(env.DB);

    const id = await createRecipeVersion(db, { domain: "example.com", script: "first" });

    expect(id).toMatch(/^rcp_[0-9a-f]{8}$/);
    expect(await getLatestRecipeVersion(db, "example.com")).toMatchObject({
      id,
      domain: "example.com",
      version: 1,
      script: "first",
    });
  });

  it("saves the next script at the next version, counted per domain", async () => {
    const db = database(env.DB);

    await createRecipeVersion(db, { domain: "example.com", script: "first" });
    await createRecipeVersion(db, { domain: "other.test", script: "elsewhere" });

    const id = await createRecipeVersion(db, { domain: "example.com", script: "second" });

    expect(await getLatestRecipeVersion(db, "example.com")).toMatchObject({
      id,
      version: 2,
      script: "second",
    });
  });

  it("fails one of two concurrent saves on the unique domain and version", async () => {
    const db = database(env.DB);

    const saves = await Promise.allSettled([
      createRecipeVersion(db, { domain: "example.com", script: "one" }),
      createRecipeVersion(db, { domain: "example.com", script: "two" }),
    ]);

    expect(saves.map(({ status }) => status).sort()).toEqual(["fulfilled", "rejected"]);
    expect(await getLatestRecipeVersion(db, "example.com")).toMatchObject({ version: 1 });
  });
});
