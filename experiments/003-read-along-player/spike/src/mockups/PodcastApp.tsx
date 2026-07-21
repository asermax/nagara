import { item, mockToc, MOCK_ACTIVE_INDEX, MOCK_ELAPSED } from "../mockData";
import { Paragraphs, Icon, fmtTime, useCenterActive } from "../ui";
import "./podcast.css";

export const PodcastApp = () => {
  const activeRef = useCenterActive();
  const pct = (MOCK_ELAPSED / item.duration) * 100;

  return (
    <div className="podcast">
      <nav className="pc-rail">
        <h4>Contents</h4>
        {mockToc.map((t) => (
          <a key={t.index} className={`lvl-${t.level}`} href="#">{t.label}</a>
        ))}
      </nav>

      <main className="pc-main">
        <article className="pc-article">
          <Paragraphs paragraphs={item.paragraphs} activeIndex={MOCK_ACTIVE_INDEX} activeRef={activeRef} />
        </article>
      </main>

      <footer className="pc-bar">
        <div className="pc-meta">
          <strong>{item.title}</strong>
          <span>mitchellh.com</span>
        </div>
        <div className="pc-controls">
          <button aria-label="Back 10 seconds"><Icon name="back10" /></button>
          <button className="pc-play" aria-label="Play"><Icon name="play" size={26} /></button>
          <button aria-label="Forward 10 seconds"><Icon name="fwd10" /></button>
        </div>
        <div className="pc-scrub">
          <span>{fmtTime(MOCK_ELAPSED)}</span>
          <div className="pc-track"><div className="pc-fill" style={{ width: `${pct}%` }} /></div>
          <span>{fmtTime(item.duration)}</span>
        </div>
      </footer>
    </div>
  );
};
