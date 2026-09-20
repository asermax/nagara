import { describe, expect, it } from "vitest";
import { parseSettlement, scriptReply } from "../src/agents/settlement.ts";

describe("settlement parsing", () => {
  it("reads a script from the last fenced json block", () => {
    const reply = `Here is the recipe:\n\n${scriptReply("export const container = 'article';")}\n\nDone.`;
    expect(parseSettlement(reply)).toEqual({
      kind: "script",
      source: "export const container = 'article';",
    });
  });

  it("reads a not-article verdict", () => {
    expect(parseSettlement('```json\n{"kind": "not-article"}\n```')).toEqual({
      kind: "not-article",
    });
  });

  it("reads a gave-up reply with its reason", () => {
    expect(
      parseSettlement('```json\n{"kind": "gave-up", "reason": "markup is unresolvable"}\n```'),
    ).toEqual({
      kind: "gave-up",
      reason: "markup is unresolvable",
    });
  });

  it("falls back to the whole text when it is bare json", () => {
    expect(parseSettlement('{"kind": "not-article"}')).toEqual({ kind: "not-article" });
  });

  it("treats an unreadable reply as giving up", () => {
    expect(parseSettlement("I could not decide.")).toEqual({
      kind: "gave-up",
      reason: "the reply carried no readable settlement",
    });
  });

  it("rejects a script settlement without source", () => {
    expect(parseSettlement('```json\n{"kind": "script"}\n```').kind).toBe("gave-up");
  });
});
