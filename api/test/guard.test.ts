import { beforeAll, describe, expect, it } from "vitest";
import { callApi } from "./helpers/api.ts";
import { clearItems, insertItem } from "./helpers/items.ts";

const ITEM_ROUTES = [
  { method: "POST", path: "/items", body: { url: "https://example.com/post" } },
  { method: "GET", path: "/items/itm_0a1b2c3d" },
  { method: "POST", path: "/items/itm_0a1b2c3d/retry" },
  { method: "GET", path: "/items/itm_0a1b2c3d/audio" },
  { method: "GET", path: "/items/itm_0a1b2c3d/images/abc123" },
];

beforeAll(async () => {
  await clearItems();
  await insertItem({ status: "ready", audio_format: "audio/ogg" });
});

describe.each([
  { keyCase: "without a key", key: null },
  { keyCase: "with a wrong key", key: "not-the-key" },
])("the key guard, $keyCase", ({ key }) => {
  it.each(ITEM_ROUTES)("answers 401 to $method $path", async ({ method, path, body }) => {
    const response = await callApi(path, { method, key, body });

    expect(response.status).toBe(401);
  });
});

describe("GET /health", () => {
  it("answers 200 without a key", async () => {
    const response = await callApi("/health", { key: null });

    expect(response.status).toBe(200);
  });
});
