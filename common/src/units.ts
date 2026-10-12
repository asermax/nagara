export type UnitWindow = {
  start?: number;
  end?: number;
};

type TextUnit = UnitWindow & {
  display: string;
  spoken: string;
};

export type ParagraphUnit = TextUnit & {
  type: "paragraph";
};

export type CodeUnit = TextUnit & {
  type: "code";
};

export type ImageUnit = TextUnit & {
  type: "image";
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
