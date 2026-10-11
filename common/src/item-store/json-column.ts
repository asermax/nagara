export const encodeJson = (value: unknown) => (value == null ? null : JSON.stringify(value));

export const decodeJson = <T>(text: string | null): T | null =>
  text == null ? null : (JSON.parse(text) as T);
