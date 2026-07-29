import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import type { Paragraph } from "../types";

interface Props {
  p: Paragraph;
  isActive: boolean;
  activeRef: React.Ref<HTMLDivElement>;
}

// Memoized so a currentTime tick (60fps) doesn't re-parse markdown: only the two
// paragraphs whose active state flips actually re-render.
export const Para = memo(({ p, isActive, activeRef }: Props) => (
  <div
    ref={isActive ? activeRef : undefined}
    className={`para ${isActive ? "active" : ""}`}
    data-index={p.index}
  >
    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[[rehypeHighlight, { detect: true }]]}>
      {p.display}
    </ReactMarkdown>
  </div>
));
