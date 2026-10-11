import { env } from "cloudflare:workers";
import { beforeAll, describe, expect, it } from "vitest";
import { callApi } from "./helpers/api.ts";
import { insertItem } from "./helpers/items.ts";

const ITEM_ROUTES = [
  { method: "POST", path: "/items" },
  { method: "GET", path: "/items/itm_0a1b2c3d" },
  { method: "POST", path: "/items/itm_0a1b2c3d/retry" },
  { method: "GET", path: "/items/itm_0a1b2c3d/audio" },
  { method: "GET", path: "/items/itm_0a1b2c3d/images/abc123" },
];

beforeAll(async () => {
  await env.DB.prepare("DELETE FROM items").run();
  await insertItem({ status: "ready", audio_format: "audio/ogg" });
});

describe("the key guard", () => {
  it.each(ITEM_ROUTES)("answers 401 to $method $path without a key", async ({ method, path }) => {
    const response = await callApi(path, {
      method,
      key: null,
      body: method === "POST" ? { url: "https://example.com/post" } : undefined,
    });

    expect(response.status).toBe(401);
  });

  it.each(ITEM_ROUTES)(
    "answers 401 to $method $path with a wrong key",
    async ({ method, path }) => {
      const response = await callApi(path, {
        method,
        key: "not-the-key",
        body: method === "POST" ? { url: "https://example.com/post" } : undefined,
      });

      expect(response.status).toBe(401);
    },
  );

  it("lets /health through without a key", async () => {
    const response = await callApi("/health", { key: null });

    expect(response.status).toBe(200);
  });
});
