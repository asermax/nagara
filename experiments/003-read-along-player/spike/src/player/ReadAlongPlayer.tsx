import { useEffect, useMemo, useRef, useState } from "react";
import { deriveToc, type Item } from "../types";
import { Icon, fmtTime } from "../ui";
import { Para } from "./Para";
import { EyeIcon } from "./EyeIcon";
import { PinIcon } from "./PinIcon";
import { useReadAlong } from "./useReadAlong";
import "./readalong.css";

interface Props {
  item: Item;
  audioSrc: string;
}

export const ReadAlongPlayer = ({ item, audioSrc }: Props) => {
  const [focus, setFocus] = useState(false);
  const player = useReadAlong(item);
  const { recenterActive } = player;
  const toc = useMemo(() => deriveToc(item.paragraphs), [item]);

  // The ToC scrolls proportionally to the article, with its edges fading when there's
  // more list off-screen in that direction.
  const tocRef = useRef<HTMLElement>(null);
  const [tocFade, setTocFade] = useState({ top: false, bottom: false });

  useEffect(() => {
    const el = tocRef.current;

    if (el == null) {
      return;
    }

    // Snap faster to the extremes: hold the ToC at top/bottom for the first/last
    // ~12% of the article rather than only at the exact ends.
    const M = 0.12;
    const eased = Math.max(0, Math.min(1, (player.scrollProgress - M) / (1 - 2 * M)));
    const max = el.scrollHeight - el.clientHeight;
    el.scrollTop = max * eased;
    setTocFade({ top: el.scrollTop > 1, bottom: max > 1 && el.scrollTop < max - 1 });
  }, [player.scrollProgress, toc]);

  // Arrows scroll only the ToC (to peek other sections), never the article. The
  // article-linked sync re-takes over as soon as the reading position moves again.
  const tocScrollTo = (where: "top" | "bottom") => {
    const el = tocRef.current;

    if (el == null) {
      return;
    }

    const max = el.scrollHeight - el.clientHeight;
    el.scrollTo({ top: where === "bottom" ? max : 0, behavior: "smooth" });
    setTocFade({ top: where === "bottom", bottom: where === "top" });
  };

  // Switching reading mode shifts the layout — re-engage follow and re-centre.
  useEffect(() => {
    recenterActive();
  }, [focus, recenterActive]);

  const currentSection = [...toc].reverse().find((t) => t.index <= player.activeIndex)?.index;
  const pct = player.duration ? (player.currentTime / player.duration) * 100 : 0;

  const onTrackClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    player.seekToTime(((e.clientX - rect.left) / rect.width) * player.duration);
  };

  return (
    <div className={`ra ${focus ? "focus" : "kapod"}`}>
      <audio ref={player.audioRef} src={audioSrc} preload="metadata" />

      <div className="ka-toc-wrap">
        {tocFade.top ? (
          <button className="toc-arrow up" onClick={() => tocScrollTo("top")} aria-label="Scroll ToC up">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 15l6-6 6 6" /></svg>
          </button>
        ) : null}

        <nav
          ref={tocRef}
          className={`ka-toc ${tocFade.top ? "fade-top" : ""} ${tocFade.bottom ? "fade-bottom" : ""}`}
        >
          {toc.map((t) => (
            <button
              key={t.index}
              className={t.index === currentSection ? "current" : ""}
              style={{ paddingLeft: `${(t.level - 1) * 0.85}rem` }}
              onClick={() => player.jumpToIndex(t.index)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {tocFade.bottom ? (
          <button className="toc-arrow down" onClick={() => tocScrollTo("bottom")} aria-label="Scroll ToC down">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg>
          </button>
        ) : null}
      </div>

      <button
        className={`focus-toggle ${focus ? "on" : ""}`}
        onClick={() => setFocus((f) => !f)}
        aria-pressed={focus}
        aria-label="Focus mode"
        title="Focus mode"
      >
        <EyeIcon open={focus} />
      </button>

      <div className="ka-scroll" ref={player.scrollRef} onScroll={player.onScroll}>
        <div className="reading">
          {item.paragraphs.map((p) => (
            <Para
              key={p.index}
              p={p}
              isActive={p.index === player.activeIndex}
              activeRef={player.activeRef}
            />
          ))}
        </div>
      </div>

      {focus ? (
        <>
          <div className="ka-fade ka-fade-top" />
          <div className="ka-fade ka-fade-bottom" />
        </>
      ) : null}

      <div className="ka-transport">
        <button aria-label="Back 10 seconds" onClick={() => player.skip(-10)}>
          <Icon name="back10" />
        </button>
        <button className="ka-play" aria-label="Play / pause" onClick={player.togglePlay}>
          <Icon name={player.playing ? "pause" : "play"} size={30} />
        </button>
        <button aria-label="Forward 10 seconds" onClick={() => player.skip(10)}>
          <Icon name="fwd10" />
        </button>
        <span className="ka-time">
          {fmtTime(player.currentTime)} / {fmtTime(player.duration)}
        </span>
        <button
          className={`follow-inline ${player.following ? "collapsed" : ""}`}
          onClick={player.followFromHere}
          aria-label="Follow from here"
          title="Follow from here"
          aria-hidden={player.following}
          tabIndex={player.following ? -1 : 0}
        >
          <PinIcon />
        </button>
      </div>

      <div className="ka-progress" onClick={onTrackClick}>
        <div style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};
