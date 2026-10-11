import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { replayCassettes } from "../testing/index.ts";
import geminiCodeDescribe from "./cassettes/gemini-code-describe.yaml?raw";
import synthesisPoll from "./cassettes/synthesis-poll.yaml?raw";

const GEMINI_URL =
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent";

const GATEWAY_BASE = "https://gateway.ai.cloudflare.com/v1/account/nagara/google-ai-studio";

const POLL_URL = "https://synthesis.test/items/itm_00000010/result?attempt=1&format=ogg";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// The recorded request, rebuilt the way a TypeScript client would: keys in another order and
// serialized without the Python client's spacing.
const rebuiltDescribeBody = () => {
  const recorded = JSON.parse(
    geminiCodeDescribe
      .split("body: '")[1]
      .split("'\n    headers:")[0]
      .replace(/\n\s+/g, " ")
      .replaceAll("''", "'"),
  );

  return JSON.stringify({
    generationConfig: recorded.generationConfig,
    contents: recorded.contents,
  });
};

const describeRequest = (url: string) =>
  fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json", "x-goog-api-key": "a-real-looking-key" },
    body: rebuiltDescribeBody(),
  });

describe("replayCassettes", () => {
  it("replays a Gemini request rebuilt in TypeScript by matching its JSON body", async () => {
    server.use(...replayCassettes(geminiCodeDescribe));

    const response = await describeRequest(GEMINI_URL);
    const body = (await response.json()) as {
      candidates: { content: { parts: { text: string }[] } }[];
    };

    expect(response.status).toBe(200);
    expect(body.candidates[0].content.parts[0].text).toContain(
      "asynchronous Python helper function",
    );
  });

  it("replays a request whose item id differs from the recording", async () => {
    server.use(...replayCassettes(synthesisPoll));

    const response = await fetch(POLL_URL.replace("itm_00000010", "itm_deadbeef"));

    expect(response.status).toBe(202);
    expect(await response.json()).toEqual({ status: "running" });
  });

  it("replays a request sent through the AI Gateway against the recorded googleapis host", async () => {
    server.use(
      ...replayCassettes(geminiCodeDescribe, {
        rewrites: { [GATEWAY_BASE]: "https://generativelanguage.googleapis.com" },
      }),
    );

    const response = await describeRequest(
      `${GATEWAY_BASE}/v1beta/models/gemini-3.5-flash-lite:generateContent`,
    );

    expect(response.status).toBe(200);
  });

  it("replays a response recorded with gzip headers without decompressing it", async () => {
    server.use(...replayCassettes(geminiCodeDescribe));

    const response = await describeRequest(GEMINI_URL);

    expect(response.headers.get("content-encoding")).toBeNull();
    expect(response.headers.get("content-length")).toBeNull();
    expect(response.headers.get("transfer-encoding")).toBeNull();
    expect(await response.json()).toMatchObject({ modelVersion: "gemini-3.5-flash-lite" });
  });

  it("answers repeated identical requests with the recorded responses in order", async () => {
    server.use(...replayCassettes(synthesisPoll));

    const first = await fetch(POLL_URL);
    const second = await fetch(POLL_URL);

    expect(first.status).toBe(202);
    expect(second.status).toBe(200);
    expect(await second.json()).toEqual({ format: "audio/ogg", duration: 12.5 });
  });

  it("fails a request the cassette does not hold", async () => {
    server.use(...replayCassettes(synthesisPoll));

    const response = await fetch(
      "https://synthesis.test/items/itm_00000010/result?attempt=2&format=ogg",
    );

    expect(response.status).toBe(500);
    expect(await response.text()).toContain("no cassette interaction matches GET");
  });
});
