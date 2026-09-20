import * as v from "valibot";

const settlementSchema = v.variant("kind", [
  v.object({
    kind: v.literal("script"),
    source: v.pipe(v.string(), v.minLength(1)),
  }),
  v.object({ kind: v.literal("not-article") }),
  v.object({
    kind: v.literal("gave-up"),
    reason: v.optional(v.string(), "no reason given"),
  }),
]);

export type Settlement = v.InferOutput<typeof settlementSchema>;

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
    const parsed = v.safeParse(settlementSchema, parseJson(block[1].trim()));
    if (parsed.success) {
      return parsed.output;
    }
  }
  const whole = v.safeParse(settlementSchema, parseJson(text.trim()));
  if (whole.success) {
    return whole.output;
  }
  return { kind: "gave-up", reason: "the reply carried no readable settlement" };
}

export function scriptReply(source: string): string {
  return `\`\`\`json\n${JSON.stringify({ kind: "script", source })}\n\`\`\``;
}
