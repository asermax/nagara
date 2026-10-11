export type ItemWorkflowParams = {
  itemId: string;
};

export const STEP = {
  fetch: "fetch",
  lease: "lease",
  recipe: "recipe",
  release: "release",
  images: "images",
  describe: "describe",
  startSynthesis: "start synthesis",
  waitForSynthesis: "wait for synthesis",
  store: "store",
} as const;

export type Step = (typeof STEP)[keyof typeof STEP];

// The lease is released right after the recipe, so restarting at either one would run the
// recipe without holding its domain's lease: both go back to asking for it.
export const restartPoint = (currentStep: Step | null): Step | null =>
  currentStep === STEP.recipe || currentStep === STEP.release ? STEP.lease : currentStep;
