import { HttpResponse } from "msw";
import type { RecordedInteraction } from "./cassette.ts";

// vcrpy stores the decoded body next to the wire's framing headers; replaying both makes fetch try
// to decompress plain text.
const FRAMING_HEADERS = new Set(["content-encoding", "content-length", "transfer-encoding"]);

const NULL_BODY_STATUSES = new Set([101, 204, 205, 304]);

export const toResponse = ({ response }: RecordedInteraction) => {
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
