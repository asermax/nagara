import mitchell from "./fixtures/mitchell.json";
import type { Item, TocEntry } from "./types";

export const item = mitchell as Item;

// The Mitchell fixture only carries 2 headings, too sparse to judge ToC *placement*
// in a static mockup. This representative list stands in purely to show each archetype's
// ToC treatment; the real heading-derived ToC + navigation is judged on the heading-rich
// fixture in Phase 2, not here.
export const mockToc: TocEntry[] = [
  { index: 0, level: 1, label: "My AI Adoption Journey" },
  { index: 2, level: 2, label: "Three phases of adoption" },
  { index: 10, level: 2, label: "Where chat falls short" },
  { index: 20, level: 2, label: "The agentic turn" },
  { index: 32, level: 2, label: "What I trust it with" },
  { index: 44, level: 2, label: "What I'm trying next" },
];

// A hardcoded "playing" position so the mockups show the highlight + progress treatment
// without any audio/sync (Phase 1 is shape-only).
export const MOCK_ACTIVE_INDEX = 12;
export const MOCK_ELAPSED = 214; // seconds, for the progress display
