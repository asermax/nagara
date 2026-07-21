# experiment-run — Nagara project extension

Additive steps for `zenku:experiment-run`. Fold these into the base flow; they never waive its core
discipline.

## Fold into Plan / Build (shaping a UI-screen experiment)

**For a screen whose question is shape/UX, explore multiple variants and mix-and-match — don't commit to
one design and transform it.** When the experiment is discovering the *shape* of a UI screen (layout,
interaction, feel), default to **breadth-then-depth**: build several **coherent whole-screen variants** as
cheap static mockups on real content, compare them side-by-side, then **recombine** — take the shell from
one, the reading surface from another, fold a rejected idea back in as a mode — and only then wire the
finalist to the real engine. Exploring and mixing ideas reliably lands a better shape than starting from a
single design and iterating it (which hill-climbs a local optimum), or committing up front and only
transforming it. Keep the variants ruthlessly static until one or two are chosen to wire; the felt,
load-bearing behaviours (sync, seek, resume) are only judged once wired.

*Provenance: learned in [experiment 003](../experiments/003-read-along-player/README.md), where four
static archetypes → mixing two of them (Karaoke shell + Podcast body) → a single player with two modes
produced the finalist; the user valued the explore-and-recombine loop over transform-a-single-start.*

**Name the confound when the builder drives.** A live builder-driven discovery loop (builder edits, user
judges the shape in real time) is high-yield for UI shape, but it is **oracle- and builder-confounded** by
construction: it validates the *shape*, never demand or that a fresh user would experience it the same.
Record that scope explicitly in the verdict; don't let a satisfying shape masquerade as validated demand.
