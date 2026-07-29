import { item, mockToc, MOCK_ACTIVE_INDEX, MOCK_ELAPSED } from "../mockData";
import { Icon, fmtTime, useCenterActive } from "../ui";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./karaoke.css";

export const Karaoke = () => {
  const activeRef = useCenterActive();
  const pct = (MOCK_ELAPSED / item.duration) * 100;

  // The section currently being read = the last ToC entry at or before the active unit.
  const currentSection = [...mockToc].reverse().find((t) => t.index <= MOCK_ACTIVE_INDEX)?.index;

  return (
    <div className="karaoke">
      {/* Floating left ToC — no button, no panel: just section titles, current one lit. */}
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

      <div className="ka-scroll">
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
      </div>

      <div className="ka-fade ka-fade-top" />
      <div className="ka-fade ka-fade-bottom" />

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
