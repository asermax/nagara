export interface Paragraph {
  index: number;
  start: number;
  end: number;
  display: string;
}

export interface Item {
  id: string;
  title: string;
  duration: number;
  paragraphs: Paragraph[];
}

export interface TocEntry {
  index: number;
  level: number;
  label: string;
}

// The ToC is derived from heading units — a unit whose display starts with '#'.
export const deriveToc = (paragraphs: Paragraph[]): TocEntry[] =>
  paragraphs
    .filter((p) => /^#{1,6}\s/.test(p.display.trim()))
    .map((p) => {
      const match = p.display.trim().match(/^(#{1,6})\s+(.*)$/);

      return {
        index: p.index,
        level: match ? match[1].length : 1,
        label: match ? match[2] : p.display,
      };
    });
