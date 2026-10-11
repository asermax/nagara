export const COST_TYPE = {
  firecrawl: "firecrawl",
  describer: "describer",
  tts: "tts",
} as const;

export type CostType = (typeof COST_TYPE)[keyof typeof COST_TYPE];

export const COST_UNIT = {
  credits: "credits",
  calls: "calls",
  seconds: "seconds",
} as const;

export type CostUnit = (typeof COST_UNIT)[keyof typeof COST_UNIT];

export type CostEntryRow = {
  id: string;
  item_id: string;
  type: CostType;
  quantity: number;
  unit: CostUnit;
  dollars: number;
  cached: boolean;
  detail: Record<string, unknown> | null;
  created_at: string;
};
