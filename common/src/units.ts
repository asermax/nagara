export type UnitWindow = {
  start?: number;
  end?: number;
};

export type ParagraphUnit = UnitWindow & {
  type: "paragraph";
  display: string;
  spoken: string;
};

export type CodeUnit = UnitWindow & {
  type: "code";
  display: string;
  spoken: string;
};

export type ImageUnit = UnitWindow & {
  type: "image";
  display: string;
  spoken: string;
  image: string;
};

export type Unit = ParagraphUnit | CodeUnit | ImageUnit;

export const DEGRADATION_REASON = {
  notFound: "404",
  timeout: "timeout",
  undecodable: "undecodable",
  describeFailed: "describe failed",
  describeCapReached: "describe cap reached",
} as const;

export type DegradationReason = (typeof DEGRADATION_REASON)[keyof typeof DEGRADATION_REASON];

export type Degradation = {
  type: Extract<Unit["type"], "image" | "code">;
  reason: DegradationReason;
  url?: string;
};
