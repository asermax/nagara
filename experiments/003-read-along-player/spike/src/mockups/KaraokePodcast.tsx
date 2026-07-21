import { item, mockToc, MOCK_ACTIVE_INDEX, MOCK_ELAPSED } from "../mockData";
import { Paragraphs, Icon, fmtTime, useCenterActive } from "../ui";
import "./karaoke.css";
import "./karaoke-podcast.css";

// Hybrid: D · Karaoke's dark immersive shell (floating left ToC + floating transport)
// with B · Podcast-app's body — a normal left-aligned scrolling column, background-fill highlight.
export const KaraokePodcast = () => {
  const activeRef = useCenterActive();
  const pct = (MOCK_ELAPSED / item.duration) * 100;
  const currentSection = [...mockToc].reverse().find((t) => t.index <= MOCK_ACTIVE_INDEX)?.index;

  return (
    <div className="karaoke kapod">
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
        <div className="kapod-article">
          <Paragraphs paragraphs={item.paragraphs} activeIndex={MOCK_ACTIVE_INDEX} activeRef={activeRef} />
        </div>
      </div>

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
