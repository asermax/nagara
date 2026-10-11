import { env } from "cloudflare:workers";
import { replayCassettes } from "@nagara/common/testing";
import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll } from "vitest";
import { geminiUrl } from "../../src/describe/core.ts";
import codeDescribe from "../cassettes/describe/test_a_real_code_describe_parses_and_is_clean.yaml?raw";

export const server = setupServer();

export const requests: string[] = [];

export const useServer = () => {
  beforeAll(() => {
    server.listen({ onUnhandledRequest: "error" });
    server.events.on("request:start", ({ request }) => {
      requests.push(`${request.method} ${request.url}`);
    });
  });
  afterEach(() => {
    server.resetHandlers();
    requests.length = 0;
  });
  afterAll(() => server.close());
};

export { codeDescribe };

const GATEWAY_PREFIX = geminiUrl(env).replace(/\/v1beta\/models\/.*$/, "");

type Interaction = { status: number; body: unknown; headers?: Record<string, string> };

// A cassette fabricated from the boundary contract, in the vcrpy shape the replay library reads:
// JSON is YAML, so it needs no serializer of its own.
export const fabricatedCassette = (
  method: string,
  uri: string,
  requestBody: unknown,
  interactions: Interaction[],
) =>
  JSON.stringify({
    interactions: interactions.map(({ status, body, headers }) => ({
      request: { method, uri, body: requestBody == null ? null : JSON.stringify(requestBody) },
      response: {
        status: { code: status },
        headers: Object.fromEntries(
          Object.entries({ "Content-Type": "application/json", ...headers }).map(
            ([name, value]) => [name, [value]],
          ),
        ),
        body: { string: typeof body === "string" ? body : JSON.stringify(body) },
      },
    })),
  });

export const firecrawlPage = (html: string, finalUrl: string) => ({
  status: 200,
  body: {
    success: true,
    data: {
      markdown: "",
      rawHtml: html,
      metadata: { url: finalUrl, sourceURL: finalUrl, creditsUsed: 1, proxyUsed: "basic" },
    },
  },
});

export const firecrawlCassette = (url: string, interactions: Interaction[]) =>
  fabricatedCassette(
    "POST",
    "https://api.firecrawl.dev/v2/scrape",
    {
      url,
      onlyMainContent: true,
      skipTlsVerification: true,
      removeBase64Images: true,
      fastMode: false,
      blockAds: true,
      storeInCache: true,
      maxAge: 14400000,
      formats: ["rawHtml", "markdown"],
      proxy: "auto",
      mobile: false,
    },
    interactions,
  );

// The recorded cassettes were made against Gemini directly; the pipeline reaches it through the
// AI Gateway.
export const replay = (...cassettes: string[]) =>
  replayCassettes(cassettes, {
    rewrites: { [GATEWAY_PREFIX]: "https://generativelanguage.googleapis.com" },
  });

export const geminiAnswer = (spoken: string) => ({
  candidates: [{ content: { parts: [{ text: JSON.stringify({ spoken }) }], role: "model" } }],
});

// The stored image's bytes come out of the Images binding, so an image describe cannot be recorded
// ahead of the run; this answers describes from the contract, by kind: code when the request has
// no inline part, otherwise by the part's mime type. A kind with no answer falls through to the
// cassettes behind this handler.
export const fabricatedDescribes = (
  answers: { code?: string; webp?: string; svg?: string },
  { cached = false } = {},
) =>
  http.post(geminiUrl(env), async ({ request }) => {
    const body = (await request.clone().json()) as {
      contents: { parts: { inlineData?: { mimeType: string } }[] }[];
    };
    const mimeType = body.contents[0].parts[1]?.inlineData?.mimeType;
    const spoken =
      mimeType == null ? answers.code : mimeType === "image/webp" ? answers.webp : answers.svg;

    return spoken == null
      ? undefined
      : HttpResponse.json(geminiAnswer(spoken), {
          headers: { "cf-aig-cache-status": cached ? "HIT" : "MISS" },
        });
  });

export const imageFiles = (files: Record<string, Uint8Array | string | number>) =>
  Object.entries(files).map(([url, file]) =>
    http.get(url, () =>
      typeof file === "number"
        ? new HttpResponse(null, { status: file })
        : new HttpResponse(file, {
            headers: { "content-type": typeof file === "string" ? "image/svg+xml" : "image/png" },
          }),
    ),
  );

export const fromBase64 = (data: string) =>
  Uint8Array.from(atob(data), (char) => char.charCodeAt(0));

export type ModalScript = {
  start?: number;
  results?: ("running" | "ready" | "short" | number)[];
  paragraphs?: number;
};

export type ModalCalls = {
  starts: { paragraphs: string[]; voice: string; destination: string; headers: Headers }[];
  results: number;
};

// Modal has no recorded cassette; these answer from the start and result contract. A ready result
// carries one window per paragraph the start received, or one fewer when the script says short; a
// script answering a synthesis started before it was installed names the paragraph count.
export const modal = ({
  start = 200,
  results = ["running", "ready"],
  paragraphs: count = 0,
}: ModalScript = {}) => {
  const calls: ModalCalls = { starts: [], results: 0 };
  let paragraphs: string[] = Array.from({ length: count }, () => "");

  const handlers = [
    http.post(env.MODAL_START_URL, async ({ request }) => {
      const body = (await request.json()) as ModalCalls["starts"][number];

      calls.starts.push({ ...body, headers: request.headers });
      paragraphs = body.paragraphs;

      return start === 200
        ? HttpResponse.json({ call_id: "fc-01TEST" })
        : new HttpResponse(null, { status: start });
    }),
    http.get(env.MODAL_RESULT_URL, () => {
      const answer = results[Math.min(calls.results, results.length - 1)];

      calls.results += 1;

      if (answer === "running") {
        return HttpResponse.json({ status: "running" }, { status: 202 });
      }

      if (typeof answer === "number") {
        return HttpResponse.json({ error: "synthesis failed" }, { status: answer });
      }

      const windows = answer === "short" ? paragraphs.length - 1 : paragraphs.length;

      return HttpResponse.json({
        format: "audio/ogg",
        duration: windows,
        timings: Array.from({ length: windows }, (_, index) => ({ start: index, end: index + 1 })),
      });
    }),
  ];

  return { calls, handlers };
};
