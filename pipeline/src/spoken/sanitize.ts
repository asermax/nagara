// CommonMark's inline-HTML tag shape, drawn on markdown-it's own boundary: `<T>`, `<br/>` and
// `<not a tag>` are tags to the parser, while `3 < 4`, `<3` and the autolink `<a@b.com>` are not.
// A tag still present in a unit's markdown is prose the author escaped rather than leaked markup:
// the words inside it are the article's own.
const SPOKEN_HTML_TAG = /<\/?([A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*?)?)\s*\/?>/g;

// A whole run of one marker character, so `**` between spaces is judged as one marker rather than
// as two asterisks that each touch the other.
const MARKER = /\*+|`+|_{2,}/g;

const OPERATOR_WORDS: Record<string, string> = {
  "<=": "less than or equal to",
  ">=": "greater than or equal to",
  "->": "to",
  "=>": "to",
  "<-": "from",
  "<<": "much less than",
  ">>": "much greater than",
  "<3": "heart",
  "<": "less than",
  ">": "greater than",
};

// `<3` only stands alone: `<30` and `<3.5` are a bound, not a heart.
const OPERATOR_GUARDS: Record<string, string> = { "<3": "(?!\\.?\\d)" };

// Longest match first, so `<=` is never read as "less than" followed by a stray `=`.
const OPERATOR = new RegExp(
  Object.keys(OPERATOR_WORDS)
    .sort((left, right) => right.length - left.length)
    .map((operator) => operator + (OPERATOR_GUARDS[operator] ?? ""))
    .join("|"),
  "g",
);

const isSpace = (character: string | undefined) => character != null && /\s/.test(character);

// An asterisk between spaces is arithmetic (`value_0 * 2`), not emphasis, so a marker is only a
// leftover when a non-space character sits on either side of it.
const touchesText = (text: string, start: number, end: number) =>
  (start > 0 && !isSpace(text[start - 1])) || (end < text.length && !isSpace(text[end]));

// A stripped marker or tag can leave a space before sentence punctuation, which goes. A dot with
// a letter or digit right after it opens a word (`.wast`, `.NET`, `.5`), so its space stays.
const collapseLine = (line: string) =>
  line
    .replace(/\s+/g, " ")
    .replace(/\s+([,;:!?]|\.(?![\p{L}\p{N}]))/gu, "$1")
    .trim();

// The same tail guards two producers: parsed markdown, whose invalid run-in emphasis leaks a
// literal marker, and the describer's structured output, which a JSON schema cannot forbid a
// marker from carrying inside its string value. A leaked marker is only ever caught by playing the
// audio, so both paths run through here.
export const sanitizeSpoken = (text: string) =>
  text
    .replace(SPOKEN_HTML_TAG, "$1")
    .replace(MARKER, (marker, offset: number, whole: string) =>
      touchesText(whole, offset, offset + marker.length) ? " " : marker,
    )
    .replace(OPERATOR, (operator) => ` ${OPERATOR_WORDS[operator]} `)
    .split("\n")
    .map(collapseLine)
    .filter((line) => line !== "")
    .join("\n");
