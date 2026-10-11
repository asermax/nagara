import { NonRetryableError } from "cloudflare:workflows";

export type SynthesisResult = {
  ready: true;
  format: "audio/ogg" | "audio/wav";
  duration: number;
  timings: { start: number; end: number }[];
};

export type SynthesisRequest = {
  paragraphs: string[];
  voice: string;
  destination: string;
};

// Proxy auth rejects a request at Modal's edge, before any container starts.
const proxyAuth = (env: Cloudflare.Env) => ({
  "Modal-Key": env.MODAL_PROXY_KEY,
  "Modal-Secret": env.MODAL_PROXY_SECRET,
});

export const startSynthesis = async (env: Cloudflare.Env, request: SynthesisRequest) => {
  const response = await fetch(env.MODAL_START_URL, {
    method: "POST",
    headers: { ...proxyAuth(env), "content-type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`modal start answered ${response.status}`);
  }

  return ((await response.json()) as { call_id: string }).call_id;
};

// A 500 is a synthesis that raised, which may not raise again; a 410 (Modal dropped the result
// after 7 days) or a 422 (a call id Modal never issued) cannot change on another attempt.
export const synthesisResult = async (
  env: Cloudflare.Env,
  callId: string,
): Promise<SynthesisResult | { ready: false }> => {
  const url = new URL(env.MODAL_RESULT_URL);

  url.searchParams.set("call_id", callId);

  const response = await fetch(url, { headers: proxyAuth(env) });

  if (response.status === 202) {
    return { ready: false };
  }

  if (response.status === 410 || response.status === 422) {
    throw new NonRetryableError(`modal result answered ${response.status}`);
  }

  if (!response.ok) {
    throw new Error(`modal result answered ${response.status}`);
  }

  return { ready: true, ...((await response.json()) as Omit<SynthesisResult, "ready">) };
};
