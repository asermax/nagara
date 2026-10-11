// A run of single letters each closed by a dot (`e.g.`, `U.S.`) is an abbreviation and keeps its
// dots. Any other dot with a letter right after it opens a file extension or joins a name's parts
// (`.wast`, `index.html`, `example.com`) when it follows a letter, a digit, whitespace, an opening
// bracket or quote, or the start of the text. A dot before a digit belongs to a number and one
// before a space or the end closes a sentence, so neither matches.
const DOT = /(?<![\p{L}\p{N}])(?:\p{L}\.){2,}|(?<=^|[\s([{"'“‘\p{L}\p{N}])\.(?=\p{L})/gu;

const isWordCharacter = (character: string | undefined) =>
  character != null && /[\p{L}\p{N}]/u.test(character);

export const speakDots = (text: string) =>
  text.replace(DOT, (match, offset: number, whole: string) => {
    if (match !== ".") {
      return match;
    }

    return isWordCharacter(whole[offset - 1]) ? " dot " : "dot ";
  });
