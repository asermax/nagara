import { item, mockToc, MOCK_ACTIVE_INDEX, MOCK_ELAPSED } from "../mockData";
import { Paragraphs, Icon, fmtTime, useCenterActive } from "../ui";
import "./immersive.css";

export const ImmersiveReader = () => {
  const activeRef = useCenterActive();

  return (
  <div className="immersive">
    <button className="im-toc-btn" aria-label="Table of contents">
      <Icon name="list" size={22} />
    </button>

    <article className="im-column">
      <Paragraphs paragraphs={item.paragraphs} activeIndex={MOCK_ACTIVE_INDEX} activeRef={activeRef} />
    </article>

    <div className="im-transport">
      <button aria-label="Back 10 seconds"><Icon name="back10" /></button>
      <button className="im-play" aria-label="Play"><Icon name="play" size={28} /></button>
      <button aria-label="Forward 10 seconds"><Icon name="fwd10" /></button>
      <span className="im-time">{fmtTime(MOCK_ELAPSED)} / {fmtTime(item.duration)}</span>
    </div>

    {/* ToC drawer shown open to convey the treatment; a real build toggles it. */}
    <aside className="im-drawer">
      <h4>Contents</h4>
      {mockToc.map((t) => (
        <a key={t.index} className={`lvl-${t.level}`} href="#">{t.label}</a>
      ))}
    </aside>
  </div>
  );
};
