import { canonicalBody } from "./canonical-body.ts";
import { normalizeIds } from "./item-id.ts";
import { byKey } from "./sort-keys.ts";

const DEFAULT_PORTS: Record<string, string> = { "http:": "80", "https:": "443" };

// Headers never take part in a match: the cassettes were recorded with the credential headers
// filtered out, so a request carrying its own credentials still matches.
export const requestKey = (method: string, uri: string, body: string | null) => {
  const url = new URL(uri);

  return JSON.stringify([
    method.toUpperCase(),
    url.protocol,
    url.hostname,
    url.port === "" ? DEFAULT_PORTS[url.protocol] : url.port,
    normalizeIds(url.pathname),
    [...url.searchParams.entries()].sort(byKey),
    canonicalBody(body),
  ]);
};
