import { describe, expect, it } from "vitest";
import { restartPoint } from "../src/workflow.ts";

describe("restartPoint", () => {
  it("restarts every step when no step has run", () => {
    expect(restartPoint(null)).toBeNull();
  });

  it("restarts a failed recipe from the lease", () => {
    expect(restartPoint("recipe")).toBe("lease");
  });

  it("restarts a failed release from the lease", () => {
    expect(restartPoint("release")).toBe("lease");
  });

  it("restarts any other step from that step", () => {
    expect(restartPoint("describe")).toBe("describe");
    expect(restartPoint("wait for synthesis")).toBe("wait for synthesis");
  });
});
