import { useState } from "react";
import { ImmersiveReader } from "./mockups/ImmersiveReader";
import { PodcastApp } from "./mockups/PodcastApp";
import { DocumentRail } from "./mockups/DocumentRail";
import { Karaoke } from "./mockups/Karaoke";
import { KaraokePodcast } from "./mockups/KaraokePodcast";
import { Player } from "./mockups/Player";
import { ReadAlongPlayer } from "./player/ReadAlongPlayer";
import type { Item } from "./types";
import mitchell from "./fixtures/mitchell.json";
import fowler from "./fixtures/fowler.json";

const MOCKUPS = [
  { key: "★", label: "★ Player · Fowler", el: <ReadAlongPlayer item={fowler as Item} audioSrc="/fowler.ogg" /> },
  { key: "M", label: "Player · Mitchell", el: <ReadAlongPlayer item={mitchell as Item} audioSrc="/mitchell.ogg" /> },
  { key: "s", label: "Player (static)", el: <Player /> },
  { key: "A", label: "A · Immersive Reader", el: <ImmersiveReader /> },
  { key: "B", label: "B · Podcast-app", el: <PodcastApp /> },
  { key: "C", label: "C · Document + rail", el: <DocumentRail /> },
  { key: "D", label: "D · Karaoke", el: <Karaoke /> },
  { key: "E", label: "E · Karaoke × Podcast", el: <KaraokePodcast /> },
] as const;

export const App = () => {
  const [active, setActive] = useState(0);

  return (
    <>
      <div className="switcher">
        {MOCKUPS.map((m, i) => (
          <button key={m.key} className={i === active ? "on" : ""} onClick={() => setActive(i)}>
            {m.label}
          </button>
        ))}
      </div>
      <div className="stage">{MOCKUPS[active].el}</div>
    </>
  );
};
