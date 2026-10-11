// Minted item ids differ on every run, so both sides are normalized before comparing; the -N
// retry suffix stays, so a reminted id never collapses onto the one it replaced.
const ITEM_ID = /itm_[0-9a-f]{8}/g;

export const normalizeIds = (text: string) => text.replace(ITEM_ID, "itm_fixed");
