const encoder = new TextEncoder();

export const hasValidKey = (request: Request, env: Cloudflare.Env) => {
  const key = encoder.encode(request.headers.get("X-API-Key") ?? "");
  const expected = encoder.encode(env.API_KEY);

  return key.byteLength === expected.byteLength && crypto.subtle.timingSafeEqual(key, expected);
};
