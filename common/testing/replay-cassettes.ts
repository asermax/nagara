import { http } from "msw";
import { parseCassette } from "./cassette.ts";
import { toResponse } from "./recorded-response.ts";
import { requestKey } from "./request-key.ts";
import { rewriteUri } from "./rewrite-uri.ts";

export type ReplayOptions = {
  rewrites?: Record<string, string>;
};

export const replayCassettes = (cassettes: string | string[], options: ReplayOptions = {}) => {
  const remaining = [cassettes]
    .flat()
    .flatMap(parseCassette)
    .map((interaction) => ({
      key: requestKey(
        interaction.request.method,
        interaction.request.uri,
        interaction.request.body,
      ),
      interaction,
    }));

  return [
    http.all("*", async ({ request }) => {
      const uri = rewriteUri(request.url, options.rewrites ?? {});
      const body =
        request.method === "GET" || request.method === "HEAD" ? null : await request.text();
      const key = requestKey(request.method, uri, body);
      const index = remaining.findIndex((recorded) => recorded.key === key);

      if (index === -1) {
        throw new Error(`no cassette interaction matches ${request.method} ${uri}`);
      }

      const [{ interaction }] = remaining.splice(index, 1);

      return toResponse(interaction);
    }),
  ];
};
