export const detail = (message: string, status: number) =>
  Response.json({ detail: message }, { status });
