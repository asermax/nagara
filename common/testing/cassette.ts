import { parse } from "yaml";

export type RecordedInteraction = {
  request: { method: string; uri: string; body: string | null };
  response: {
    status: { code: number };
    headers?: Record<string, string[]>;
    body: { string: string };
  };
};

export const parseCassette = (cassette: string) =>
  (parse(cassette) as { interactions: RecordedInteraction[] }).interactions;
