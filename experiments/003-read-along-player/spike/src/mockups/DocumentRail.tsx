import { item, mockToc, MOCK_ACTIVE_INDEX, MOCK_ELAPSED } from "../mockData";
import { Paragraphs, Icon, fmtTime, useCenterActive } from "../ui";
import "./document.css";

export const DocumentRail = () => {
  const activeRef = useCenterActive();
  const pct = (MOCK_ELAPSED / item.duration) * 100;

  return (
    <div className="document">
      <main className="doc-main">
        <article className="doc-article">
          <Paragraphs paragraphs={item.paragraphs} activeIndex={MOCK_ACTIVE_INDEX} activeRef={activeRef} />
        </article>
      </main>

      <aside className="doc-rail">
        <div className="doc-controls">
          <button aria-label="Back 10 seconds"><Icon name="back10" size={22} /></button>
          <button className="doc-play" aria-label="Play"><Icon name="play" size={24} /></button>
          <button aria-label="Forward 10 seconds"><Icon name="fwd10" size={22} /></button>
        </div>
        <div className="doc-progress">
          <div className="doc-track"><div className="doc-fill" style={{ width: `${pct}%` }} /></div>
          <span>{fmtTime(MOCK_ELAPSED)} / {fmtTime(item.duration)}</span>
        </div>
        <h4>Contents</h4>
        <nav>
          {mockToc.map((t) => (
            <a key={t.index} className={`lvl-${t.level}`} href="#">{t.label}</a>
          ))}
        </nav>
      </aside>
    </div>
  );
};
