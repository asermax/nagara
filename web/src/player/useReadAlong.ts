import { useCallback, useEffect, useRef, useState } from "react";
import type { Item } from "../types";

const activeIndexAt = (item: Item, t: number): number => {
  const ps = item.paragraphs;
  let lo = 0;
  let hi = ps.length - 1;
  let found = 0;

  while (lo <= hi) {
    const mid = (lo + hi) >> 1;

    if (ps[mid].start <= t) {
      found = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }

  return found;
};

const posKey = (id: string) => `nagara-pos-${id}`;

// Land just past a unit's start: an exact seek can round down below the boundary,
// leaving the *previous* unit active.
const SEEK_NUDGE = 0.05;

export const useReadAlong = (item: Item) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(item.duration);
  const [playing, setPlaying] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [following, setFollowing] = useState(true);
  const [scrollProgress, setScrollProgress] = useState(0);

  // Refs mirror state so event/rAF callbacks read the latest without re-subscribing.
  const followingRef = useRef(following);
  followingRef.current = following;
  const programmatic = useRef(false);

  // rAF sync loop: the <audio> clock drives the active unit. timeupdate (~4Hz) is too
  // coarse for the ≤200ms tolerance, so we poll currentTime every frame instead.
  useEffect(() => {
    let raf = 0;

    const tick = () => {
      const audio = audioRef.current;

      if (audio) {
        setCurrentTime(audio.currentTime);
        setActiveIndex((prev) => {
          const next = activeIndexAt(item, audio.currentTime);

          return next === prev ? prev : next;
        });
      }

      const c = scrollRef.current;

      if (c) {
        const max = c.scrollHeight - c.clientHeight;
        const p = max > 0 ? c.scrollTop / max : 0;

        setScrollProgress((prev) => (Math.abs(prev - p) < 0.001 ? prev : p));
      }

      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(raf);
  }, [item]);

  // Restore saved position once metadata is known; persist on pause/unload.
  useEffect(() => {
    const audio = audioRef.current;

    if (audio == null) {
      return;
    }

    const onMeta = () => {
      setDuration(audio.duration || item.duration);
      const saved = Number(localStorage.getItem(posKey(item.id)) ?? 0);

      if (saved > 0 && saved < (audio.duration || item.duration)) {
        audio.currentTime = saved;
      }
    };

    const onPlay = () => setPlaying(true);
    const onPause = () => {
      setPlaying(false);
      localStorage.setItem(posKey(item.id), String(audio.currentTime));
    };

    audio.addEventListener("loadedmetadata", onMeta);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);

    if (audio.readyState >= 1) {
      onMeta();
    }

    return () => {
      audio.removeEventListener("loadedmetadata", onMeta);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
    };
  }, [item]);

  // Auto-follow: keep the active unit centred while engaged. Flag the programmatic
  // scroll so its own scroll events don't count as the user taking manual control.
  useEffect(() => {
    if (!following) {
      return;
    }

    programmatic.current = true;
    activeRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
    const timer = setTimeout(() => {
      programmatic.current = false;
    }, 700);

    return () => clearTimeout(timer);
  }, [activeIndex, following]);

  const onScroll = useCallback(() => {
    if (programmatic.current) {
      return;
    }

    if (followingRef.current) {
      setFollowing(false);
    }
  }, []);

  // While disengaged, re-engage auto-follow once the active unit has been back in
  // view for a short dwell — so scrolling back to the playing spot resumes following
  // without needing the pill.
  useEffect(() => {
    if (following) {
      return;
    }

    let dwell: ReturnType<typeof setTimeout> | null = null;

    const clearDwell = () => {
      if (dwell) {
        clearTimeout(dwell);
        dwell = null;
      }
    };

    const check = () => {
      const container = scrollRef.current;
      const el = activeRef.current;

      if (container == null || el == null) {
        return;
      }

      const c = container.getBoundingClientRect();
      const e = el.getBoundingClientRect();
      const inView = e.top < c.bottom - 48 && e.bottom > c.top + 48;

      if (inView && dwell == null) {
        dwell = setTimeout(() => setFollowing(true), 1200);
      } else if (!inView) {
        clearDwell();
      }
    };

    const container = scrollRef.current;
    container?.addEventListener("scroll", check);
    const poll = setInterval(check, 400);
    check();

    return () => {
      container?.removeEventListener("scroll", check);
      clearInterval(poll);
      clearDwell();
    };
  }, [following]);

  // Re-engage auto-follow and snap the active unit back to centre — used when the
  // reading mode changes (the layout shifts, so the active line must be re-centred).
  const recenterActive = useCallback(() => {
    setFollowing(true);
    programmatic.current = true;
    activeRef.current?.scrollIntoView({ block: "center", behavior: "auto" });
    setTimeout(() => {
      programmatic.current = false;
    }, 500);
  }, []);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;

    if (audio == null) {
      return;
    }

    if (audio.paused) {
      void audio.play();
    } else {
      audio.pause();
    }
  }, []);

  const skip = useCallback((delta: number) => {
    const audio = audioRef.current;

    if (audio) {
      audio.currentTime = Math.max(0, Math.min(audio.duration || Infinity, audio.currentTime + delta));
    }
  }, []);

  const seekToTime = useCallback((t: number) => {
    const audio = audioRef.current;

    if (audio) {
      audio.currentTime = t;
    }
  }, []);

  // Seek-to-here: jump audio to the unit nearest the reading position and re-engage
  // follow. Deliberately does NOT change play/pause state.
  const followFromHere = useCallback(() => {
    const container = scrollRef.current;
    const audio = audioRef.current;

    if (container == null || audio == null) {
      return;
    }

    const mid = container.clientHeight / 2;
    let best = 0;
    let bestDist = Infinity;

    container.querySelectorAll<HTMLElement>(".para").forEach((el) => {
      const center = el.offsetTop - container.scrollTop + el.offsetHeight / 2;
      const dist = Math.abs(center - mid);

      if (dist < bestDist) {
        bestDist = dist;
        best = Number(el.dataset.index);
      }
    });

    const target = item.paragraphs.find((p) => p.index === best);

    if (target) {
      audio.currentTime = target.start + SEEK_NUDGE;
      setFollowing(true);
    }
  }, [item]);

  // ToC jump: seek to a unit's start and scroll it into view, re-engaging follow —
  // also without changing play/pause state.
  const jumpToIndex = useCallback((index: number) => {
    const audio = audioRef.current;
    const container = scrollRef.current;
    const target = item.paragraphs[index];

    if (audio == null || target == null) {
      return;
    }

    audio.currentTime = target.start + SEEK_NUDGE;
    setFollowing(true);
    programmatic.current = true;
    container?.querySelector<HTMLElement>(`.para[data-index="${index}"]`)?.scrollIntoView({
      block: "center",
      behavior: "smooth",
    });
    setTimeout(() => {
      programmatic.current = false;
    }, 700);
  }, [item]);

  return {
    audioRef,
    scrollRef,
    activeRef,
    onScroll,
    currentTime,
    duration,
    playing,
    activeIndex,
    following,
    scrollProgress,
    togglePlay,
    skip,
    seekToTime,
    followFromHere,
    jumpToIndex,
    recenterActive,
  };
};
