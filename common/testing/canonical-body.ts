import { normalizeIds } from "./item-id.ts";
import { sortKeys } from "./sort-keys.ts";

// A body rebuilt in TypeScript serializes its JSON differently from the Python client that
// recorded it, so JSON bodies compare by value and anything else compares as text.
export const canonicalBody = (body: string | null) => {
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
