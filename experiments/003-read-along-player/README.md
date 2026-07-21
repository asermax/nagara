# 003 — Read-along player: what shape makes read-along work?

**Question**: Driven by the real M1/M2 item contract, **what player shape makes read-along actually
work** — where does the right combination of paragraph highlighting, transport, markdown rendering,
and a scroll-decoupled navigation model (seek-to-here "follow" pill + floating table of contents +
±10s skip + resume) land, judged on real generated items? This is **discovery-mode**: the *judgment*
below is fixed; the *shape* is what the experiment discovers. The timing data was proven exact at the
data level in 001 — unproven is whether it renders into a player that holds together and feels like
read-along.

**Hypothesis**: A simple React player consuming `paragraphs[].{index,start,end,display}` + `duration` +
audio can deliver a read-along experience that works and coheres, carrying navigation on the
scroll-decoupled model alone (free scroll + seek-to-here pill + ToC + ±10 s) **without** click-to-seek.
(This is a single-arm bet — click-to-seek is not built, so the test is whether its absence creates
friction, not a head-to-head against it.) It is **disproven** if any of these is observed:

1. **Highlight can't track** — the active paragraph drifts or jitters against `currentTime` badly
   enough to break the read-along feel: the highlight can't be kept on the correct unit within a small
   tolerance across the whole article, or fails to re-lock immediately after a seek.
2. **Markdown and highlight can't coexist** — rendered display markdown (headings, emphasis, links,
   lists — and blockquote/code/table on the synthetic probe) can't be highlighted cleanly per-unit, or
   the active-unit highlight mangles the rendered formatting.
3. **The navigation model fails** — seek-to-here lands on the wrong audio position; the follow pill's
   appear/dismiss logic fights the reader; the ToC can't be derived from headings or targets the wrong
   unit; or ±10s skip desyncs highlight from audio.
4. **The shape doesn't cohere** (insight-level) — fired by observable anchors: resume restores the
   **wrong unit**; an affordance (seek-to-here pill, ToC, ±10 s) is built but goes **unused across a
   full-article read**; or the scroll-decoupled model creates enough friction that I find myself
   **reaching for a click-to-seek that isn't there**. (The "feels like read-along" / "wow moment"
   language elsewhere is commentary on these observables, not the bar the verdict rests on.)

**Judging** — two lenses, judged against the **running player rendering real generated items** (item
JSON + Opus audio snapshotted from the M1/M2 API), not mock content:

| Fixture | Type | What it stresses |
|---|---|---|
| [My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey) | clean article (001/002 e2e fixture) | highlight sync + transport + scroll/follow, the baseline read-along |
| [Revisiting No Silver Bullets…](https://newsletter.pragmaticengineer.com/p/revisiting-no-silver-bullets-in-the) | heading-rich long-form (001 fixture) | markdown render + highlight coexistence + a real ToC to navigate (swappable in `/experiment-run` if it disappoints) |
| **Synthetic probe** — hand-crafted item JSON w/ a blockquote, a fenced code block, and a table (plausible timing) | hostile constructs | render + highlight of the construct classes the pipeline hasn't yet generated end-to-end |

- **Task criterion** (concrete, checkable against the real player):
  1. Play a real item start→finish: the highlighted unit advances **in sync** — the active unit matches
     the audio's `[start, end)` window within a fixed tolerance (highlight switches within **≤ 200 ms**
     of the boundary), including immediately **after a seek**, and highlighting ends when audio ends.
  2. **Markdown renders and highlights** — headings, emphasis, links, and lists render from `display` and
     the active unit highlights correctly over the rendered markdown. The synthetic probe additionally
     shows blockquote / code / table render + highlight.
  3. **Navigation lands correctly** — scroll away → follow pill appears → seek-to-here jumps audio to
     that unit's `start`, resumes, and re-engages follow; ±10 s moves audio and the highlight follows;
     a ToC entry jumps to its heading unit's `start`. Each lands on the correct audio position.
  4. **Resume** — reload the page → playback position is restored (from localStorage) to the correct
     unit/time.
- **Insight criterion**: What player *shape* emerged? Which navigation affordances (seek-to-here pill,
  ToC, ±10 s) earn their place once built, and which felt redundant or went unused? Did the
  scroll-decoupled model (seek-to-here + ToC + ±10 s) carry navigation on its own, or did I keep
  reaching for a click-to-seek that isn't there? Does the whole thing land as the "wow moment"
  read-along, or does something (jitter, awkward markdown, nav friction) break the spell? And did the contract carry everything the player
  needed, or did a gap surface (a per-unit `type` field for ToC/code styling, word-level timing, real
  backend resume) — routed to `BACKLOG.md` / milestone notes.
- **Synthetic probe (scope note)**: blockquote / code / table have only been validated *strip-level* in
  002 — no real item carrying them has been generated end-to-end (open in `BACKLOG.md`). So the
  **real items own the verdict**; the hand-crafted synthetic item keeps disproof #2 honest at the
  **render/highlight level only**. End-to-end generation of a formatting-heavy real item stays deferred
  to the M2 backlog and is *not* a gate on this experiment.
- **Kill / timebox**: ≤ ~4–5 focused sessions, **build time inside the box** (one for mockup breadth +
  selection, the rest to wire and judge). The spike is a greenfield React app plus a set of static
  mockups, highlight-sync, markdown render, three navigation modes, and resume — real work; if it
  eats the box before the shape questions get exercised, that overrun is itself a signal. **The verdict
  is never gated on wiring a second archetype**: take **one** finalist through all four tasks + a full
  end-to-end read first; wire the second only if the box allows, as a shape-comparison bonus (1 is
  sufficient, 2 is upside). If highlight sync against a real `<audio>` element **can't be made smooth
  enough** within the box, the finding is that read-along needs a different sync approach (or word-level
  timing) — record it and route it. If the shape hasn't cohered by the end of the box, that is the result.

## Setup

**Discovery-mode — the shape is the finding; the judgment above is fixed.** The functional floor was
agreed up front (highlight, play/pause + progress, markdown render, ±10 s skip, scroll "follow from
here" pill = **seek-to-here**, floating ToC, resume); click-to-seek is deliberately **out**, replaced by
the scroll-decoupled model. How those combine into a coherent player is what gets discovered and judged —
by **generating several UI alternatives to compare**, not by committing to one shape up front.

**Method: breadth-then-depth (mockups → wire).** First generate **several static layout mockups** —
different treatments of the reading surface, highlight style, control placement, and ToC presentation —
rendered with a real item's content, so the shape can be thought through visually and side-by-side.
Narrow to **1–2 finalists**, then **wire only those** to the shared functional core and judge the felt
read-along. The mockup phase produces the shape-selection insight; the load-bearing disproofs (highlight
sync, seek feel, coherence) are only reachable once wired, so a static mockup is never the final verdict.

**Agreed shape (build contract, converged in `/experiment-run`)** — the cheapest thing that answers the
question; everything the judging doesn't test is faked, hardcoded, or static:

- **Stack**: a standalone **Vite + React + TS** app with **one screen** — the player. Plain CSS
  (throwaway; **not** Panda-CSS), a markdown-render lib. **Not** the `web/` TanStack app.
- **Phase 1 — four static mockups** of the player screen, each a **coherent whole-shape archetype**
  (layout + highlight style + controls + ToC presentation vary together), rendered from the **real**
  Mitchell content with a **hardcoded active unit** and full static chrome (ToC open, controls visible),
  **no audio/sync**:
  - **A · Immersive Reader** — centered column, dimming-as-highlight, minimal floating transport, ToC as
    a slide-in drawer.
  - **B · Podcast-app** — persistent bottom player bar (full transport + scrubber), background-fill
    highlight, left ToC rail.
  - **C · Document + side rail** — document body + persistent right rail (ToC + progress + controls),
    left-accent-border highlight, nothing overlays content.
  - **D · Karaoke / teleprompter** — active paragraph pinned centre and enlarged, content auto-scrolls
    past a fixed reading position.
- **Phase 2 — one shared functional core** wired into the **1–2 chosen** archetypes:
  - **Highlight sync** — an `<audio>` element as clock; the active unit derived from `currentTime`
    against the paragraph `[start, end)` windows. **Unknown only building resolves, validate first in
    Session B**: the browser `timeupdate` event fires only ~every 250 ms — coarser than the ≤ 200 ms
    criterion — so the highlight loop must be driven off **`requestAnimationFrame` polling `currentTime`**
    (not `timeupdate`). Question: can rAF-polled `currentTime` hold the active unit within 200 ms across a
    14-min file and **re-lock after `seeked`**? (A `timeupdate`-artifact miss must not be misread as
    "read-along can't sync".)
  - **Markdown render** — render each unit's `display` markdown; the ToC is **derived client-side** from
    the heading units (a unit whose `display` starts with `#`), each heading's `start` its seek target
    (no `type` field exists in the contract).
  - **Navigation** — the scroll "follow from here" pill (**seek-to-here**) + ±10 s skip. No click-to-seek.
  - **Resume** — current time persisted to **localStorage**, keyed by item id; the real `PATCH`-position
    backend endpoint is deferred to `BACKLOG.md`.
- **Real data** (static fixture files in the spike — no live API / auth / CORS). Each unit is
  `{index, start, end, display}`; the player renders `display`:
  | Fixture | Source | Exercises |
  |---|---|---|
  | `mitchell` | **reuse** `experiments/002-.../out/{timeline.json, audio.ogg}` (55 units, ~14 min, emphasis/links, 2 headings) | sync, transport, markdown emphasis, nav, resume |
  | `heading-rich` | **generate** via the 002 pipeline (`modal.Cls.from_name("nagara-tts","Kokoro")`) on a section-heavy article — heading density **verified before spending synthesis**; URL pre-registered as Pragmatic Engineer "Revisiting No Silver Bullets", swappable | markdown headings + a real ToC to navigate |
  | `synthetic` | **hand-crafted** item (blockquote + fenced code block + table, plausible fixed timing); its highlight is driven by a **hardcoded clock** (no audio, no Modal synthesis — no timing criterion rests on it) | render + highlight of those construct classes (**render-level only**, per the scope note above) |

**Deliberate deviation from graduate-in-place.** The project's `## zenku` convention is spike-at-root in
`web/`, hardened in place. This experiment intentionally uses an **isolated throwaway spike** instead: the
player's uncertainty is shape/UX/functionality, which a simple React app answers **without** first
committing the full TanStack Start + Panda-CSS + react-query stack. Graduation to `web/` is a **rewrite**
undertaken only on a promote verdict — building the production stack before the shape is proven would be
wasted motion.

**Session protocol** — breadth-then-depth; scorable tasks run against the **wired** player, interleaved
with open reflection:

1. **Session A (breadth — mockups)**: generate several static UI mockups (layout / highlight style /
   control placement / ToC presentation) rendered from a real item's content, and compare them
   side-by-side. Pick 1–2 finalists to wire. → *"Which shape reads as read-along and why? What made a
   layout feel right or wrong before anything moved?"* (Selection insight — no task criterion yet.)
2. **Session B (wire the core — baseline read-along)**: build the shared sync engine + highlight into the
   chosen shape on the clean fixture. Run **task 1** (sync start→finish). → *"What do I understand now
   about highlight fidelity in a real browser that I didn't from the exact-at-data-level 001 result?"*
3. **Session C (markdown + ToC)**: add markdown render + the derived ToC on the heading-rich fixture; run
   **task 2** and the ToC half of **task 3**; run the synthetic probe for blockquote/code/table render.
   → *"Does displayed formatting help or distract while listening? Does the ToC earn its place?"*
4. **Session D (navigation model + resume + coherence)**: add the scroll follow-pill (seek-to-here) +
   ±10 s skip and localStorage resume; run the rest of **task 3** and **task 4**; do a full end-to-end
   read of a real article. → *"Did the scroll-decoupled model carry navigation on its own, or did I keep
   reaching for a click-to-seek that isn't there? Does this cohere into the wow-moment read-along — what
   affordance is redundant, what's missing, what gap did the contract expose?"*

**Spike location**: `experiments/003-read-along-player/spike/` — an isolated, throwaway Vite + React app
(deliberate deviation from the project's `web/` graduate-in-place convention; graduation to `web/`
deferred to a promote verdict, as a rewrite).

## Notes

_The insight log — appended live while running. Dated discoveries, and expected insights that did not
materialize. The verdict is judged against this record, not memory._

**2026-07-21 · Session A (mockup breadth) — live builder-driven discovery.** All four archetypes
(A Immersive / B Podcast-app / C Document+rail / D Karaoke) built as static mockups on the real
Mitchell content and reviewed side-by-side in the browser.
- **Strong early signal: D · Karaoke visuals are the favourite.** The pinned-centre, enlarged active
  line with dim past/upcoming and fade gradients read best. (First archetype to draw a clear positive.)
- **Adjustment on D**: move the ToC to a **floating left-side** treatment — no button, no panel, just
  floating section titles — with the **current section title highlighted**. Replaces D's original bare
  `[≡]` button. Rationale: keep the immersive teleprompter surface uncluttered while still giving
  always-visible section orientation.
- **Floating-ToC applied to D** and confirmed landing. Next: staying in mockup mode to keep tweaking
  (not yet wiring), per the user.
- **New hybrid requested — E · Karaoke × Podcast**: keep D's dark immersive shell (floating left ToC +
  floating transport) but swap the teleprompter body (pinned-centre, enlarged single line, dim
  past/upcoming) for **B · Podcast-app's body treatment** — a normal left-aligned scrolling reading
  column with a **background-fill** active highlight. Probes whether the immersive dark shell works with
  a calmer, scroll-normal reading surface rather than the aggressive centre-pin.
- **D made scrollable**: the teleprompter was a fixed no-scroll window; user wants to scroll the whole
  article in the Karaoke variant too. Now renders the full article in an inner scroller with the active
  line centred on load; fades / floating ToC / transport stay fixed over the scroll. (Early UX note: the
  aggressive per-line dim + centre-pin was coupled to the fixed window; free scrolling loosens that
  teleprompter feel — a tension to watch when judging D vs E.)
- **E converged (live tweaks), and is pulling ahead as the likely finalist.** Sequence of asks:
  (1) remove dimming on non-current text — inactive paragraphs read at full brightness; (2) remove the
  top/bottom fade gradients entirely; (3) widen the reading column (40 → 52rem). Result: a **calm dark
  immersive reader** — no dimming, no fades, a single **background-fill** highlight on the active
  paragraph, floating left ToC (current section lit), floating transport. **Insight forming**: the
  *shell* the user wants is Karaoke's (dark, immersive, floating ToC + transport), but the *reading
  surface* they keep steering toward is calm and scroll-normal (Podcast-style), not the teleprompter's
  dim/centre-pin drama. The "wow" is quiet legibility inside an immersive frame, with highlight as the
  only motion — the aggressive teleprompter treatment was over-designed.
- **Both D and E**: reading column widened to 52rem; floating ToC moved from vertically-centred to
  **top-left**.
- **Consolidated inventory (authoritative, supersedes running log above where they conflict)** — static
  mockups on real Mitchell content, hardcoded active unit, no audio:
  - **A · Immersive Reader** — light, centred column, dimming-as-highlight, floating transport, ToC
    slide-in drawer. Built, not favoured.
  - **B · Podcast-app** — light, left ToC rail, bottom player bar, background-fill highlight. Built; its
    *body treatment* fed the E hybrid.
  - **C · Document + rail** — light, right rail (ToC + controls), left-accent highlight. Built, not favoured.
  - **D · Karaoke** — dark, teleprompter body (centre-pinned, enlarged active, dim past/upcoming, top/bottom
    fades), scrollable, floating top-left ToC (current section lit), floating transport, 52rem. Built.
  - **E · Karaoke × Podcast** (**current favourite**) — dark immersive shell (floating top-left ToC +
    floating transport) with a **calm scroll-normal body**: no dim, no fades, full-brightness text,
    background-fill highlight on the active paragraph only, 52rem column. Built.
- **Build-status**: all five are static mockups; nothing wired to audio/sync yet (Phase 2 pending finalist
  lock). The load-bearing sync/nav disproofs remain unexercised by design until wiring.

**2026-07-21 · Finalist locked — one player, two reading modes.** Rather than pick D *or* E, the shape
converged on **a single player with a `focus` toggle**:
- **Default = E** (calm scroll-normal reader: full-brightness text, background-fill highlight, no dim/fades)
  — cleaner and easier to read for sustained listening.
- **Focus mode = D** (teleprompter: current paragraph centred + enlarged, past/upcoming dimmed, fades) —
  a lot more centred on the current paragraph for when the listener wants to lock on.
- **Shared shell** (both modes): dark immersive background, floating top-left ToC (current section lit),
  floating transport, progress bar; switching modes re-centres on the active unit.
This is the shape to **wire in Phase 2** (built as `Player` with the focus toggle; A–E kept as reference
mockups). Insight: the earlier D-vs-E "tension" resolved into *modes of one player*, not competing shapes —
calm-by-default with an opt-in high-focus treatment.

**2026-07-21 · Scope boundary reaffirmed — shape, not design.** User flagged that what these mockups
answer is **shape** (layout, UX, usability, the mode structure), *not* visual design. The aesthetic in the
spike (dark warm palette, type scale, spacing, the fill/dim treatments) is a **deliberate placeholder,
never under test** — some aspects are liked, but "proper design" (design language, typography, colour,
motion, brand) is a **separate question routed to its own experiment** (captured in `BACKLOG.md`), not a
widening of 003. 003's verdict is about whether the *shape* delivers read-along, judged on real content;
the visual treatment carries no verdict weight.

**2026-07-21 · Session B/C (wired) — the finalist wired to the real engine.** Built a `player/` module
(`useReadAlong` hook + memoized `Para` + `ReadAlongPlayer`) wired to the **real Mitchell Opus** audio.
Task results against real content:
- **Task 1 — sync ≤ 200 ms (load-bearing): PASS, comfortably.** Highlight driven by **`requestAnimationFrame`
  polling `currentTime`** (not `timeupdate`). Measured highlight lag at two known boundaries (u2→u3 @21.75 s,
  u3→u4 @39.55 s): **26 ms and 19 ms** — ~1–2 frames, far inside 200 ms. The rAF-vs-`timeupdate` unknown is
  resolved: rAF holds the active unit tight and **re-locks after seek** immediately (verified after skip and
  after progress-bar seek). Per-paragraph `memo` keeps the 60 fps tick from re-parsing markdown.
- **Task 3 — navigation lands: PASS.** ±10 s skip moves audio and the highlight follows (re-lock confirmed:
  t≈52 s → correct unit 4); progress-bar click seeks; the **scroll follow-pill (seek-to-here)** appears on
  manual scroll, and clicking it jumps audio to the unit at the reading position (→ t≈171 s, unit 11),
  resumes, and re-engages auto-follow (pill dismisses). *Caveat:* the ToC is still wired to the **placeholder**
  `mockToc` — real heading-derived ToC navigation needs the heading-rich fixture (below), still owed.
- **Task 4 — resume: PASS.** Position persisted to `localStorage` (`nagara-pos-mitchell`) on pause; after a
  full reload the audio restored to 171.69 s exactly.
- **Task 2 — markdown render + highlight: PARTIAL (as expected).** Mitchell's inline emphasis, links, and its
  2 headings render and highlight correctly in both modes (run-in bold + italic confirmed on screen).
  **Still owed**: (a) the **heading-rich** real fixture for a genuine multi-entry ToC, and (b) the **synthetic
  probe** (blockquote / code / table) for render + highlight of those construct classes.
- **Focus toggle**: E-default ↔ D-teleprompter switch works live and re-centres on the active unit.

Build-status: wired player is the default `★` tab; static mockups A–E + static Player kept as reference.
**Remaining to close 003**: heading-rich fixture (real ToC) + synthetic probe (blockquote/code/table render).

**2026-07-21 · Wiring refinements (live builder-driven round) — consolidated, authoritative.** A dense
set of adjustments while driving the wired player; all built + verified in-browser:
- **Follow-from-here is now an inline transport button** (📍 emoji), appearing only when scrolled away —
  not a separate floating pill.
- **Auto-follow re-engages on its own** after the active unit has been back in view for a ~1.2 s dwell
  (scroll back to the playing spot and following resumes without the pill).
- **Follow-from-here and ToC jump do NOT change play/pause state** (verified: paused stays paused, seek
  lands at the reading position) — seeking is decoupled from transport.
- **ToC is derived from the article's real headings** (`deriveToc`), and **a ToC click seeks + scrolls**
  to that heading. (On Mitchell that's only 2 entries — a genuine multi-entry ToC still needs the
  heading-rich fixture; the wiring is correct, the fixture is the gap.)
- **Focus-mode enlargement is now `transform: scale(1.4)`, not `font-size`** — verified the active unit is
  `matrix(1.4,…)` with font-size identical to siblings, so growing the active line **no longer reflows**
  surrounding text (fixes the reflow the user flagged).
- **Focus toggle = a bare SVG eye** (own `EyeIcon`): a dim closed-lid eye when off, an accent-coloured open
  eye scaled up ~1.5× with a springy transition when on. No background, border, or status circle.
- **Non-focus (E) mode: removed the oversized top/bottom whitespace** — starts near the top like an
  article, keeping only bottom clearance so the last unit isn't hidden behind the transport.

**2026-07-21 · Responsiveness + control polish (live round 2).**
- **Follow button = SVG location pin** (solid teardrop, no hole), icon-only; **the control bar animates
  its expansion** (the follow button collapses its own width when following, so the transport grows/shrinks
  smoothly instead of snapping).
- **Focus toggle = custom SVG eye** (`EyeIcon`): closed lid + lashes when off; when on, an open almond +
  pupil with **8 radial lashes evenly distributed around the eye**, offset for a wide-open look, scaled up
  ~1.5× in accent colour — verified rendered.
- **Mobile (`@media max-width:700px`)**: ToC hidden; horizontal margins widened so the focus zoom has room;
  **focus zoom made subtler** (scale 1.4→1.12) and reading text reduced; control bar made smaller/shorter.
  *Harness caveat*: `agent-browser`'s viewport override didn't reflow the layout here, so the mobile
  breakpoint is unverified in-browser — the CSS is standard and correct, but a real-device check is owed.
- **Scope note**: several round-2 tweaks are *shape/UX/usability* (mobile behaviour, follow-in-transport,
  animated bar, focus-on-mobile) and **in scope**; the finer icon aesthetics (eye lash geometry, pin shape,
  colours) are **visual-design polish** — out of 003's scope per the shape-not-design boundary, carrying no
  verdict weight, and really a preview of the captured *read-along player visual design* experiment.

**2026-07-21 · Rich fixture — Task 2 closed end-to-end.** Generated a second **real** item via the 002
Modal pipeline: **Martin Fowler, "Micro Frontends"** (`gen_fixture.py` → `fowler.json` 172 units +
`fowler.ogg`, ~40 min). Chosen after a cheap `precheck.py` richness scan ranked candidates by construct
counts (Fowler: 31 headings, 19 code blocks, 20 list items — far richer than Pragmatic Engineer's 5
headings/0 code; two other candidates failed extraction). Wired as its own `★ Player · Fowler` tab (the
player was parameterised to take `{item, audioSrc}`). Verified in-browser:
- **Real multi-level ToC** — 31 entries derived from actual headings, **nested** (h1/h2/h3 indent), current
  section lit, ToC click seeks + scrolls. This was the main task-2 gap; now closed on real content.
- **Code blocks render** — 19 `<pre>` blocks render (dark code styling); lists, headings, inline bold all
  render + highlight correctly.
- **Sync holds on the long article** — highlight tracks `currentTime` on the 40-min / 172-unit item.
- **Still synthetic-only**: **blockquote** and **table** (Fowler has neither) — their render+highlight is
  covered only by the pre-registered synthetic probe, which was **not built**. Minor residual.

**2026-07-21 · ToC + code polish on the rich fixture (round 3).**
- **ToC bug — off-by-one on click**: seeking to a unit's exact `start` can round *down* below the boundary,
  leaving the previous unit active. Fixed with a small **seek nudge** (+0.05 s) in `jumpToIndex` /
  `followFromHere`.
- **ToC indentation was inverted** (only an `lvl-2` rule existed, so h2 indented but deeper h3 didn't).
  Now indents **by level inline** (`(level-1)·0.85rem`) — deeper = more indented.
- **ToC overflow → proportional scroll**: with 31 entries the list overflowed; replaced its own scrollbar
  with a **scroll linked proportionally to the article scroll** (article-progress drives `tocRef.scrollTop`),
  and **edge fades** (mask gradient) that appear only when there's more list off-screen that way.
- **Inline code** restyled for the dark surface (a base light-background rule was leaking).
- **Syntax highlighting added** — `rehype-highlight` (`detect:true`) + a github-dark theme; verified 479
  token spans on Fowler's HTML code blocks, pre supplies the surface, theme colours the tokens.

**2026-07-21 · ToC navigation model (round 4).** The long (31-entry) ToC drove a small design of its own:
- **Proportional scroll** — the ToC scroll is linked to the article scroll (not its own scrollbar), with an
  **easing that snaps to the top/bottom faster** (holds the extremes over the first/last ~12% of the article).
- **Edge fades** (mask gradients) appear only when there's more list off-screen that way.
- **Jump arrows** at the faded top/bottom edges scroll **only the ToC** (to peek other sections) — they do
  **not** move the article or change playback; the article-linked position re-takes over once reading moves.
- **Root-cause bug (graduation-relevant)**: the wired player reuses the mockups' `ka-*` class names, and
  `karaoke.css`'s **global** `.ka-toc { position:absolute; top:2rem }` leaked in, pulling the nav out of its
  wrapper (a phantom 32 px offset + uncapped height → ToC ran off-page). Fixed by overriding in `.ra .ka-toc`.
  **Lesson for graduation**: the real `web/` build must **scope or rename** these shared class names — the
  throwaway spike's global CSS is not safe to carry over verbatim.

**2026-07-21 · Final prototype.** ToC jump-arrows moved **outside** the list (in-flow above/below), and
focus-mode paragraph gap widened (2.4→4rem) so the scaled active line has breathing room. **Fowler is now
the default `★` tab** (the rich real article is the canonical demo; Mitchell kept as a second real fixture).
Prototype considered done by the user.

**2026-07-21 · Closing corrections (pre-verdict honesty pass).**
- **Synthetic probe was not built — departure recorded.** The plan was a hand-crafted blockquote/code/table
  item to cover those constructs at render level. In practice the rich Fowler fixture was expected to carry
  them, so the probe was skipped — but Fowler turned out to have **code only** (no blockquote, no table).
  Net: **code** is validated end-to-end on real content; **blockquote and tables remain unjudged**
  (disproof #2 was exercised for headings/emphasis/links/lists/code and is **unjudgeable** for
  blockquote/table). Not a pass for those two — an untested gap.
- **Navigation "never reached for click-to-seek" is builder judgment, not a logged user reflection.** The
  navigation *mechanics* were verified to land (seek-to-here, ToC seek+scroll, ±10 s, re-lock). The felt
  "the scroll-decoupled model carried nav and I never missed a click-to-seek" is the builder's impression
  across informal use, not a pre-registered Session-D reflection captured live — and under the
  builder/oracle confound it is not evidence a fresh user wouldn't miss it.
- **Task 1 sub-clause** "highlight clears when audio ends" was **not separately checked** (sync lag +
  post-seek re-lock were).

## Verdict

**PROMOTE — the read-along player shape is proven.** A single player with **two reading modes** cohered as
the finalist: **E-default** (calm scroll-normal reader, background-fill highlight) with an opt-in
**focus-mode** teleprompter (centre-pinned, transform-scaled active line), inside a dark immersive shell
with a floating heading-derived ToC (nested, article-linked proportional scroll, edge fades, out-of-list
jump arrows), a floating transport, a scroll-decoupled **seek-to-here follow-pill**, ±10 s skip, and
localStorage resume — consuming the **M1/M2 contract unchanged** (`paragraphs[].{index,start,end,display}`
+ `duration` + audio; ToC from `#`-prefixed units).

**Against the pre-registered criteria** (judged from the insight log): **no disproof condition triggered
where it could be exercised.** Task lens — **1 (sync ≤200 ms + re-lock): PASS** (measured 19–26 ms;
"highlight clears at audio end" not separately checked); **3 (navigation lands): PASS** (seek-to-here, ToC
seek+scroll, ±10 s); **4 (resume): PASS** (localStorage restored exactly); **2 (markdown render+highlight):
PARTIAL — PASS for headings/emphasis/links/lists/code end-to-end on real fixtures (Mitchell + Fowler);
blockquote and tables UNJUDGED** (Fowler carried neither, and the pre-registered synthetic
blockquote/code/table probe was not built — so disproof #2 was exercised for prose/headings/lists/code and
is *unjudgeable* for blockquote/table, not passed). Insight lens — the shape cohered into *modes of one
player*; the scroll-decoupled model's navigation mechanics all landed and (builder's judgment, under the
confound) it never left the builder reaching for a click-to-seek; and the contract carried everything the
player needed (the only surfaced gaps: resume wants a real backend endpoint — deferred; and no per-unit
`type` field was needed — ToC derives from the `#` prefix).

**Scope (how far this reaches):** self-use, one extended **builder-driven** session, **two real articles**
(Mitchell — clean, ~14 min; Fowler "Micro Frontends" — rich, 31 headings/19 code blocks, ~40 min), a
**throwaway Vite+React spike** (deliberate deviation from graduate-in-place). It is **oracle- and
builder-confounded** by construction — the builder built and the user judged — so it validates the *shape,
UX, and functional contract*, **not** demand and **not** that a fresh user would experience it the same.
Visual design was explicitly out of scope (its own captured experiment).

**Therefore — Promote the shape to `PRODUCT.md` Milestone 2** (folded in with the markdown content layer it
renders). Graduation to the real `web/` TanStack app is a **rewrite**, and must **scope/rename the shared
`ka-*` CSS classes** the spike reused globally (a leak bit us mid-run). Residuals routed to `BACKLOG.md`:
blockquote + table end-to-end validation, focus-mode polish for non-prose constructs (centred lists/code look wrong),
player real-device mobile check, resume-position backend endpoint, LLM-explanation spoken form for code
blocks, and playback-speed control. Word-level highlighting was **dropped** from the backlog. The
explore-multiple-variants-and-recombine method that produced the finalist was captured as a durable
convention in `.zenku/experiment-run.md`.
