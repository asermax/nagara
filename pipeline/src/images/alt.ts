import { isUnspeakable } from "../spoken/typed-units.ts";

const LIST_ITEM = /^\s*([-*+]|\d+\.)\s+/;
const HEADING = /^\s*#{1,6}\s+/;

// CMS boilerplate that reads as a sentence but says nothing about the image: it separates "Image
// of tank rolling over a world map" (kept) from "This article appears in the October 2023 issue.
// Subscribe to WIRED." (described), both grammatical sentences.
const ALT_DENYLIST = ["subscribe", "appears in", "courtesy", "photograph by", "click"];

const ALT_FILENAME = /\.(jpe?g|png|gif|webp|svg|avif|bmp|tiff?)\b/i;

export const normalizeTitle = (title: string | null) => (title ?? "").trim().toLowerCase();

export const imageSpoken = (alt: string) =>
  alt === "" ? "Image with no description." : `Image: ${alt}`;

// Compared without a leading heading or list marker, which would otherwise defeat the title match.
export const isCruft = (text: string, titleNorm: string) => {
  const core = text.replace(HEADING, "").replace(LIST_ITEM, "").trim();

  return (titleNorm !== "" && core.toLowerCase() === titleNorm) || isUnspeakable(core);
};

// Several words, and not comma-separated keyword soup.
const readsAsSentence = (alt: string) => {
  if (alt.split(/\s+/).length < 3) {
    return false;
  }

  const fragments = alt.split(",").filter((fragment) => fragment.trim() !== "");

  return !(
    fragments.length >= 3 && fragments.every((fragment) => fragment.trim().split(/\s+/).length <= 2)
  );
};

// Conservative on purpose: an alt is spoken verbatim only when it reads as a sentence, is not the
// article title and clears the denylist; everything else goes to the describer.
export const isGoodAlt = (rawAlt: string, titleNorm: string) => {
  const alt = rawAlt.trim();
  const lower = alt.toLowerCase();

  return (
    alt !== "" &&
    !isCruft(alt, titleNorm) &&
    !ALT_DENYLIST.some((phrase) => lower.includes(phrase)) &&
    !ALT_FILENAME.test(alt) &&
    readsAsSentence(alt)
  );
};
