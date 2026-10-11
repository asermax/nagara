import { HttpResponse, http } from "msw";
import { parse } from "yaml";

type RecordedInteraction = {
  request: { method: string; uri: string; body: string | null };
  response: {
    status: { code: number };
    headers?: Record<string, string[]>;
    body: { string: string };
  };
};

export type ReplayOptions = {
  rewrites?: Record<string, string>;
};

// Minted item ids differ on every run, so both sides are normalized before comparing; the -N
// retry suffix stays, so a reminted id never collapses onto the one it replaced.
const ITEM_ID = /itm_[0-9a-f]{8}/g;

// vcrpy stores the decoded body next to the wire's framing headers; replaying both makes fetch try
// to decompress plain text.
const FRAMING_HEADERS = new Set(["content-encoding", "content-length", "transfer-encoding"]);

const NULL_BODY_STATUSES = new Set([101, 204, 205, 304]);

const DEFAULT_PORTS: Record<string, string> = { "http:": "80", "https:": "443" };

const normalizeIds = (text: string) => text.replace(ITEM_ID, "itm_fixed");

const byKey = ([left]: [string, unknown], [right]: [string, unknown]) => left.localeCompare(right);

const sortKeys = (value: unknown): unknown => {
  if (Array.isArray(value)) {
    return value.map(sortKeys);
  }

  if (value != null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(byKey)
        .map(([key, entry]) => [key, sortKeys(entry)]),
    );
  }

  return value;
};

// A body rebuilt in TypeScript serializes its JSON differently from the Python client that
// recorded it, so JSON bodies compare by value and anything else compares as text.
const canonicalBody = (body: string | null) => {
  if (body == null || body === "") {
    return null;
  }

  const normalized = normalizeIds(body);

  try {
    return JSON.stringify(sortKeys(JSON.parse(normalized)));
  } catch {
    return normalized;
  }
};

// Headers never take part in a match: the cassettes were recorded with the credential headers
// filtered out, so a request carrying its own credentials still matches.
const requestKey = (method: string, uri: string, body: string | null) => {
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

const rewrite = (uri: string, rewrites: Record<string, string>) => {
  const prefix = Object.keys(rewrites).find((candidate) => uri.startsWith(candidate));

  return prefix == null ? uri : `${rewrites[prefix]}${uri.slice(prefix.length)}`;
};

const toResponse = ({ response }: RecordedInteraction) => {
  const headers = new Headers();

  for (const [name, values] of Object.entries(response.headers ?? {})) {
    if (!FRAMING_HEADERS.has(name.toLowerCase())) {
      for (const value of values) {
        headers.append(name, value);
      }
    }
  }

  return new HttpResponse(
    NULL_BODY_STATUSES.has(response.status.code) ? null : response.body.string,
    { status: response.status.code, headers },
  );
};

export const replayCassettes = (cassettes: string | string[], options: ReplayOptions = {}) => {
  const remaining = [cassettes]
    .flat()
    .flatMap(
      (cassette) => (parse(cassette) as { interactions: RecordedInteraction[] }).interactions,
    )
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
      const uri = rewrite(request.url, options.rewrites ?? {});
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
