export type Settlement =
  | { kind: "script"; source: string }
  | { kind: "not-article" }
  | { kind: "gave-up"; reason: string };

function toSettlement(value: unknown): Settlement | null {
  if (typeof value !== "object" || value == null) {
    return null;
  }
  const reply = value as Record<string, unknown>;
  if (reply.kind === "script") {
    if (typeof reply.source !== "string" || reply.source.length === 0) {
      return null;
    }
    return { kind: "script", source: reply.source };
  }
  if (reply.kind === "not-article") {
    return { kind: "not-article" };
  }
  if (reply.kind === "gave-up") {
    const reason = typeof reply.reason === "string" ? reply.reason : "no reason given";
    return { kind: "gave-up", reason };
  }
  return null;
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export function parseSettlement(text: string): Settlement {
  const fenced = [...text.matchAll(/```[a-zA-Z]*\n?([\s\S]*?)```/g)];
  for (const block of fenced.reverse()) {
    const settlement = toSettlement(parseJson(block[1].trim()));
    if (settlement != null) {
      return settlement;
    }
  }
  const whole = toSettlement(parseJson(text.trim()));
  if (whole != null) {
    return whole;
  }
  return { kind: "gave-up", reason: "the reply carried no readable settlement" };
}

export function scriptReply(source: string): string {
  return `\`\`\`json\n${JSON.stringify({ kind: "script", source })}\n\`\`\``;
}
