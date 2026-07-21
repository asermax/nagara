import { useEffect, useRef, useState } from "react";
import { item, mockToc, MOCK_ACTIVE_INDEX, MOCK_ELAPSED } from "../mockData";
import { Paragraphs, Icon, fmtTime } from "../ui";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./karaoke.css";
import "./karaoke-podcast.css";
import "./player.css";

// The finalist: one player, two reading modes.
//   default → E (calm scroll-normal reader, background-fill highlight)
//   focus   → D (teleprompter: current paragraph centred + enlarged, dim past/upcoming)
export const Player = () => {
  const [focus, setFocus] = useState(false);
  const activeRef = useRef<HTMLDivElement>(null);
  const pct = (MOCK_ELAPSED / item.duration) * 100;
  const currentSection = [...mockToc].reverse().find((t) => t.index <= MOCK_ACTIVE_INDEX)?.index;

  // Re-centre on the active unit whenever the mode changes (and on mount).
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "center" });
  }, [focus]);

  return (
    <div className={`karaoke player ${focus ? "focus" : "kapod"}`}>
      <nav className="ka-toc">
        {mockToc.map((t) => (
          <a
            key={t.index}
            href="#"
            className={`lvl-${t.level} ${t.index === currentSection ? "current" : ""}`}
          >
            {t.label}
          </a>
        ))}
      </nav>

      <button
        className={`focus-toggle ${focus ? "on" : ""}`}
        onClick={() => setFocus((f) => !f)}
        aria-pressed={focus}
      >
        Focus
      </button>

      <div className="ka-scroll">
        {focus ? (
          <div className="ka-stream">
            {item.paragraphs.map((p) => (
              <div
                key={p.index}
                ref={p.index === MOCK_ACTIVE_INDEX ? activeRef : undefined}
                className={`para ${p.index === MOCK_ACTIVE_INDEX ? "active" : ""}`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{p.display}</ReactMarkdown>
              </div>
            ))}
          </div>
        ) : (
          <div className="kapod-article">
            <Paragraphs paragraphs={item.paragraphs} activeIndex={MOCK_ACTIVE_INDEX} activeRef={activeRef} />
          </div>
        )}
      </div>

      {focus ? (
        <>
          <div className="ka-fade ka-fade-top" />
          <div className="ka-fade ka-fade-bottom" />
        </>
      ) : null}

      <div className="ka-transport">
        <button aria-label="Back 10 seconds"><Icon name="back10" /></button>
        <button className="ka-play" aria-label="Play"><Icon name="play" size={30} /></button>
        <button aria-label="Forward 10 seconds"><Icon name="fwd10" /></button>
        <span className="ka-time">{fmtTime(MOCK_ELAPSED)} / {fmtTime(item.duration)}</span>
      </div>
      <div className="ka-progress"><div style={{ width: `${pct}%` }} /></div>
    </div>
  );
};
