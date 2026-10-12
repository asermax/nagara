import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";
import { callApi } from "./helpers/api.ts";
import { clearItems, insertItem } from "./helpers/items.ts";

const imageLocation = (response: Response) => new URL(response.headers.get("Location") ?? "");

beforeEach(clearItems);

describe("GET /items/{id}/images/{hash}", () => {
  it("redirects to a GET URL signed for the image's key even before the item is ready", async () => {
    const id = await insertItem({ status: "generating", current_step: "describe" });

    const response = await callApi(`/items/${id}/images/abc123`);
    const location = imageLocation(response);

    expect(response.status).toBe(307);
    expect(location.pathname).toBe(`/${env.R2_BUCKET}/images/abc123`);
    expect(location.searchParams.get("X-Amz-Expires")).toBe("3600");
  });

  it("answers 404 for an unknown item", async () => {
    const response = await callApi("/items/itm_ffffffff/images/abc123");

    expect(response.status).toBe(404);
  });

  it("redirects an unknown hash too, leaving the miss to R2", async () => {
    const id = await insertItem({ status: "ready", audio_format: "audio/ogg" });

    const response = await callApi(`/items/${id}/images/0000unknown`);

    expect(response.status).toBe(307);
    expect(imageLocation(response).pathname).toBe(`/${env.R2_BUCKET}/images/0000unknown`);
  });
});
