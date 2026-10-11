import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { callApi } from "./helpers/api.ts";
import { clearItems, insertItem } from "./helpers/items.ts";

beforeEach(clearItems);

describe("GET /items/{id}/audio", () => {
  it("redirects a ready item to a GET URL signed for its audio key for one hour", async () => {
    const id = await insertItem({ status: "ready", audio_format: "audio/ogg", duration: 12 });

    const response = await callApi(`/items/${id}/audio`);
    const location = new URL(response.headers.get("Location") ?? "");

    expect(response.status).toBe(307);
    expect(location.origin).toBe(env.R2_S3_ENDPOINT);
    expect(location.pathname).toBe(`/${env.R2_BUCKET}/audio/${id}`);
    expect(location.searchParams.get("X-Amz-Expires")).toBe("3600");
    expect(location.searchParams.get("X-Amz-Signature")).toMatch(/^[0-9a-f]{64}$/);
  });

  it("answers 404 for an item still generating", async () => {
    const id = await insertItem({ status: "generating", current_step: "wait for synthesis" });

    const response = await callApi(`/items/${id}/audio`);

    expect(response.status).toBe(404);
  });
});
