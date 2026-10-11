import type { Unit } from "@nagara/common";
import { isGoodAlt, normalizeTitle } from "../images/alt.ts";

export type DescribeJob = {
  index: number;
  kind: "code" | "image";
};

const DISPLAYED_ALT = /^!\[(.*)\]\(/s;

export const altOf = (display: string) => DISPLAYED_ALT.exec(display)?.[1] ?? "";

// One document-ordered list of every code unit and every image without a good alt is what makes
// the cap one budget shared by both kinds.
export const describeJobs = (units: Unit[], title: string | null, cap: number) => {
  const titleNorm = normalizeTitle(title);
  const jobs = units.flatMap((unit, index): DescribeJob[] => {
    if (unit.type === "code") {
      return [{ index, kind: "code" }];
    }

    return unit.type === "image" && !isGoodAlt(altOf(unit.display), titleNorm)
      ? [{ index, kind: "image" }]
      : [];
  });

  return { described: jobs.slice(0, cap), capped: jobs.slice(cap) };
};
