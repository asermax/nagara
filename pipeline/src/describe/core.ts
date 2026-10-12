import { NonRetryableError } from "cloudflare:workflows";
import { sanitizeSpoken } from "../spoken/sanitize.ts";

const MODEL = "gemini-3.5-flash-lite";

type Part = { text: string } | { inlineData: { mimeType: string; data: string } };

type GenerateResponse = {
  candidates?: { content?: { parts?: { text?: string }[] } }[];
};

// 408 and 429 mean unlucky and 5xx means the far side is briefly down; any other 4xx means the
// call itself is wrong, so another attempt only spends the budget.
const isTransient = (status: number) => status === 408 || status === 429 || status >= 500;

export const geminiUrl = (env: Cloudflare.Env) =>
  `https://gateway.ai.cloudflare.com/v1/${env.CLOUDFLARE_ACCOUNT_ID}/${env.CLOUDFLARE_GATEWAY_ID}/google-ai-studio/v1beta/models/${MODEL}:generateContent`;

// Structured output rules out a heading or a preamble, but a JSON schema cannot forbid a marker
// inside the string value, so the value still runs through the sanitize tail.
export const describe = async (env: Cloudflare.Env, parts: Part[]) => {
  const response = await fetch(geminiUrl(env), {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "cf-aig-authorization": `Bearer ${env.CLOUDFLARE_API_KEY}`,
    },
    body: JSON.stringify({
      contents: [{ parts, role: "user" }],
      generationConfig: {
        responseMimeType: "application/json",
        responseSchema: {
          properties: { spoken: { type: "STRING" } },
          required: ["spoken"],
          type: "OBJECT",
        },
      },
    }),
  });

  if (!response.ok) {
    const message = `gemini answered ${response.status}`;

    throw isTransient(response.status) ? new Error(message) : new NonRetryableError(message);
  }

  const body = (await response.json()) as GenerateResponse;
  const text = body.candidates?.[0]?.content?.parts?.[0]?.text;

  if (text == null || text === "") {
    throw new NonRetryableError("gemini answered an empty response");
  }

  return {
    spoken: sanitizeSpoken((JSON.parse(text) as { spoken: string }).spoken),
    cached: response.headers.get("cf-aig-cache-status")?.toUpperCase() === "HIT",
  };
};
