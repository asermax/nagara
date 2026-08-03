---
title: "The quest log"
tags:
  - index
summary: "The backlog: adventures, quests, and how work moves through them."
---

# The quest log

Everything not yet done lives here, in one list. This folder is nagara's quest log. These are **records rather than notes**: they say what we did and what we intend to do, they go stale by design, and the writing charter in [[the vault index]] does not apply to them.

A **quest** is one session's work. An **adventure** is too big and too foggy for that, and carries a destination plus the **trials** standing between here and it.

Adventures come in two kinds, and an adventure's `kind` says which:

- A **journey** clears ground. Its destination is knowing how to build the thing, and it holds research, design and spike quests. Never a build quest. Run it with `zenku:travel`.
- A **raid** builds. Its destination is the thing working, and it holds build quests. Run it with `zenku:raid`.

A journey is usually followed by a raid, which reads its solved quests, reconciles them into one shape, and slices that into the build quests it lands one per session. Either can stand alone: a feature with no open questions is a raid nobody had to clear ground for.

Most things captured here start as quests. An adventure appears when something turns out to have trials in it.

An embed shows one view at a time. This is what is takeable now; the others are at the bottom of this page.

![[quest-log.base]]

## How work moves

```
log ─┬─ a loose quest ── design ── build ── a note
     │
     └─ a journey ── destination ── bearings ── trials ── quests
                                                            │
                                  one per session, each     │
                                  settling its own piece ───┘
                                            │
                            no trials left, nothing in reach
                                            │
                                     the ground is clear
                                            │
        a raid ── reconcile ── destination ── bearings ── build quests
                                            │
                                  one slice per session
                                            │
                              one note ── strike the worktree
```

Two rules govern that, and both belong to the framework rather than to this project: **find the path**, decisions before deliverables, which the two kinds enforce by construction because a journey cannot hold a build quest; and **keep the pace**, one quest per session, research excepted.

## Where the shape lives

A quest carries a `## Design`: the technical detail it settles or builds, down to the types and signatures.

**An adventure carries none.** A decision lives in exactly one place, the quest that settled it, and nothing is ever copied upward. The adventure's solved index points at those quests instead, one line each, which is what keeps it short enough to read on the twelfth session as easily as the second.

The whole shape gets reconciled **once**, at the start of the raid: every one of the journey's solved quests read together, the disagreements between them settled, and the result sliced into build quests. That reconciliation goes into no file. It is agreed in the conversation and it becomes the slices.

**The durable note is written at the very end of the raid, out of every quest's design at once**, the journey's and the raid's together, when the thing is built and can be described in the present tense. No quest writes one on the way there, not even a build quest, because a page per slice describes parts of a shape nobody has seen whole and reconciling those afterwards costs more than writing it once.

So a mid-flight effort has no single place its shape lives, deliberately: it does not have a coherent design yet, and a section pretending otherwise gets read as one.

## Which quests are takeable

A quest is **in reach** when it is open, unclaimed, and nothing is blocking it. That is the first view of the index, and it is the only list worth reading when choosing what to do next.

`blocked_by` names the quests that must be solved first, as **bare kebab-case filenames**, no brackets and no path. One fixed form matters because clearing the field is a search. `adventure` takes the same bare form, for the same reason.

It **empties as its blockers close**, instead of accumulating history. That is what lets the index answer "what can I take" without following a chain, and the order things actually happened is preserved in the solved index and in git.

**Emptied means `blocked_by: []`, never a bare `blocked_by:`.** The In-reach and Blocked views split on whether that list is empty, and a null is neither: a quest written that way disappears from both at once, which is the one failure nothing here will show you.

## Naming and frontmatter

Named in kebab-case after the thing itself, unique across the whole vault, per [[the vault index]].

**The tag is what classifies a record.** `adventure` or `quest`, and the index reads nothing else to tell them apart, so a record with the wrong tag lands in the wrong views or in none. Per [[the vault index]], that failure is silent.

Every record carries `title` and `summary` like everything else in the vault. **The summary is what the index shows**, in the one column a reader scans, so write it as a line about the work rather than about the note.

An **adventure** carries `status`, `kind`, `priority` and `created`. **`kind` is `journey` or `raid`, and every adventure states it.** Both index views query it positively, so one with no kind lands in neither and shows up nowhere: that absence is how you find it, and filling it in is the whole fix. Its statuses:

- `open` — being worked, or waiting to be.
- `done` — the destination was reached and built.
- `closed` — the destination stopped being worth reaching. The note says why, and **what would reopen it**.

A **quest** carries `status`, `kind`, `adventure`, `blocked_by`, `priority` and `created`. Its statuses:

- `open` — not started.
- `claimed` — a session is on it. Claimed before any work, so a concurrent session skips it.
- `solved` — answered or built. The answer is on the quest itself.
- `dropped` — no longer worth doing, with a line saying why.

A quest's `kind` says how it gets solved. Both record kinds share the field — the tag is what says which vocabulary applies (`journey`/`raid` for an adventure, the four below for a quest):

| Kind | Solved by |
|---|---|
| `research` | Reading primary sources. The one kind that runs several at once. |
| `design` | Settling a shape in text: modules, seams, data flow, types. |
| `spike` | Throwaway code in the adventure's worktree, to find something out. |
| `build` | Writing a vertical slice of the real thing. |

Anything that resolves by talking it through is a `design` quest most of the time; where it is genuinely just a decision, say so in the quest and settle it in conversation. Work that has to happen outside the repo before a decision can be made — provisioning access, signing up for something, moving data — is a `build` quest whose slice is that errand.

**`priority` is `1-now`, `2-soon` or `3-later`.** The numbers are there so the index sorts on them: the values are text, and without a prefix an ascending sort puts `later` above `now`.

## Nothing stays here after it ends

An **effort** is a journey, the raid that followed it, and every quest under both. When it ends, its records are **struck**: deleted, in one commit named after the effort. A solved loose quest is an effort of one and goes the same way as soon as it lands. So this folder holds only the work in flight, and there is no archive folder in it and no archived status.

A record that ended reads exactly like one that is live to anything searching by name or content, which is most of what a session does before it decides anything. Emptying the folder is what keeps that search honest, and it is why a status alone is not enough: it hides a dead record from an index without hiding it from a search.

**git is the archive.** A struck record is recoverable in full from history: `git log --diff-filter=D -- docs/quest-log/` lists the endings, newest first, and `git show <sha>^:docs/quest-log/<record>.md` reads any record back exactly as it stood.

One rule falls out of that, and it applies while writing notes rather than at an ending: **nothing outside an effort may link into it.** A note citing a quest dangles the moment that quest is struck, and a dangling link is the one cost git does not cover. A note gives the reason itself rather than the record that settled it.

## What is not written here

**No ordering artifact and no planning document.** Order comes from `priority` and from what is in reach.

**An adventure is never converted into a quest, or the reverse by hand.** `zenku:travel` rewrites the note from the other template and says it did, so the change is visible in one diff.

**The explanation of how something works does not live here.** When a quest settles something durable, the explanation goes into the notes, per [[the vault index]], and the quest stays where it is as the record of how we found out.

## How we work

Anything learned about the *process* instead of the product lands here, as a short subsection. This is the only place the way we work is written down, so a habit that lives in someone's head is a habit the next session does not have.

### Spikes are throwaway, one worktree per effort

nagara ran its first three experiments under the opposite convention: **graduate-in-place**, spikes built directly in `api/` and `web/` and hardened where they landed, because the TTS pipeline's technical risk was already spent and a rewrite looked like wasted motion. It cost something the project's own record noticed: [[player-ready-item]]'s findings say plainly that under graduate-in-place, the spike "absorbed substantial production-hardening inside the timebox (pydantic-settings, module packages, `APIKeyHeader` auth on all routes, ~17 tests, ruff/ty, a dropped dependency)"; a signal that "spike" had come to mean near-production code, budgeted for accordingly rather than genuinely cheap. [[read-along-player-shape]] then deliberately broke from that convention on its own (an isolated throwaway Vite+React app) and turned in the most cleanly scoped of the three, exercising a shape question without first committing the real stack.

The quest log now runs throwaway spikes, one worktree per effort on a branch that is never merged, inherited by the raid that follows and struck when that raid ends, and the real thing is built once the answers are in. This reverses the project's own original convention on the evidence of its own first spike, not on the plugin's default.

### Pre-register a synthetic probe when the real artifact cannot reach a case

When the real work artifact cannot exercise a load-bearing disproof condition (a fixture that happens not to contain the hostile case, an article missing the construct a hypothesis hinges on), that condition is unfalsifiable as written, and a criterion that cannot fail proves nothing. Pre-register a **minimal synthetic probe** built to trigger exactly that case, and mark it explicitly as separate from the real-artifact judgment: the real data still owns the verdict; the probe only keeps the disproof honest. Say plainly what the probe covers (often strip- or transform-level only) and what stays deferred, so the scope does not silently narrow. Reach for this only when the real artifact genuinely cannot reach the case, never as a substitute for real data.

Learned in [[markdown-paragraph-pipeline]], where the clean-HTML fixture contained no code blocks or blockquotes and a mandatory synthetic snippet caught a blockquote-strip bug the real article never could.

### For a UI-shape question, explore several variants and recombine them

When the quest is discovering the *shape* of a UI screen (layout, interaction, feel), default to **breadth-then-depth**: build several coherent whole-screen variants as cheap static mockups on real content, compare them side-by-side, then **recombine** (take the shell from one, the reading surface from another, fold a rejected idea back in as a mode), and only then wire the finalist to the real engine. Exploring and mixing ideas reliably lands a better shape than starting from a single design and iterating it, which hill-climbs a local optimum. Keep the variants ruthlessly static until one or two are chosen to wire; the felt, load-bearing behaviours are only judged once wired.

Learned in [[read-along-player-shape]], where four static archetypes recombined into a single player with two modes (a calm reader by default, an opt-in focus teleprompter), a shape neither archetype was on its own.

A live builder-driven discovery loop (builder edits, user judges the shape in real time) is high-yield for exactly this kind of question, but it is **oracle- and builder-confounded** by construction: it validates the shape, never demand or that a fresh user would experience it the same. Name that confound in the verdict; do not let a satisfying shape masquerade as validated demand.

## Spikes outlive the quest that made them

**One effort owns one spike worktree**, on a branch that is never merged, and every spike under it works in there. The journey's first spike creates it. Spikes compound, and a fresh checkout each time orphans whatever the last one fetched or cached, so the second question ends up paying for the first one twice.

It **outlives the journey**. The raid that follows inherits it, because the build is exactly who wants to go and look at what was measured. Each spike names what it added to the tree in its answer, so the answer and the place to go and look at it sit together. A prose answer loses whatever nobody thought to write down, and the later questions, what exactly did we run and did we try the other adapter, are answerable in seconds from a live checkout.

**The raid strikes it**, after the durable note is written and never before. A journey nobody raids strikes its own when it closes. Either way, anything that mattered has to be in that note or in the solved quests by then, because that is the last moment it is recoverable.

## The rest of the index

- **Blocked** — open, waiting on something. `![[quest-log.base#Blocked]]`
- **Journeys** — ground being cleared. `![[quest-log.base#Journeys]]`
- **Raids** — things being built. `![[quest-log.base#Raids]]`
- **Claimed** — a session took it and has not come back. `![[quest-log.base#Claimed]]`
- **Ended** — every terminal status: a quest solved or dropped, an adventure done or closed. `![[quest-log.base#Ended]]`

Embed any of those under a heading of its own to have it on this page.

Two are worth checking rather than browsing. **Claimed** finds anything that seems to have vanished: a quest claimed and never finished sits in no other view. **Ended** is a cleanup list rather than a history — because records are struck when their effort ends, anything sitting in it is either mid-session or an ending somebody left half-finished. It should be short, and it should empty.

---

Related: [[the vault index]]
