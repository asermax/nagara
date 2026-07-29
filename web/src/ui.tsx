import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Paragraph } from "./types";

// Opens each archetype at the reading position so its highlight treatment is
// visible on load (Phase-1 mockups have no playback to scroll there on their own).
export const useCenterActive = () => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollIntoView({ block: "center" });
  }, []);

  return ref;
};

export const fmtTime = (secs: number): string => {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);

  return `${m}:${s.toString().padStart(2, "0")}`;
};

interface ParagraphsProps {
  paragraphs: Paragraph[];
  activeIndex: number;
  activeRef?: React.Ref<HTMLDivElement>;
}

export const Paragraphs = ({ paragraphs, activeIndex, activeRef }: ParagraphsProps) => (
  <>
    {paragraphs.map((p) => (
      <div
        key={p.index}
        ref={p.index === activeIndex ? activeRef : undefined}
        className={`para ${p.index === activeIndex ? "active" : ""}`}
        data-index={p.index}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{p.display}</ReactMarkdown>
      </div>
    ))}
  </>
);

// Inline SVG transport glyphs so the mockups read as a real player with zero deps.
export const Icon = ({ name, size = 24 }: { name: string; size?: number }) => {
  const paths: Record<string, React.ReactNode> = {
    play: <path d="M8 5v14l11-7z" />,
    pause: <path d="M6 5h4v14H6zm8 0h4v14h-4z" />,
    back10: (
      <>
        <path d="M12 5V1L7 6l5 5V7a6 6 0 1 1-6 6H4a8 8 0 1 0 8-8z" />
        <text x="12" y="16" fontSize="7" textAnchor="middle" fill="currentColor" stroke="none">10</text>
      </>
    ),
    fwd10: (
      <>
        <path d="M12 5V1l5 5-5 5V7a6 6 0 1 0 6 6h2a8 8 0 1 1-8-8z" />
        <text x="12" y="16" fontSize="7" textAnchor="middle" fill="currentColor" stroke="none">10</text>
      </>
    ),
    list: <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z" />,
  };

  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      {paths[name]}
    </svg>
  );
};
