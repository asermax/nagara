---
title: "The lab"
tags:
  - lab
  - index
summary: "The two backlogs (objectives we do not yet know how to reach, and work that is already decided) and how each one gets done."
---

# The lab

Two backlogs, and the split between them is the load-bearing part of this folder.

**An idea** is an **objective** (something we want to be able to do) together with the **unknowns** standing between us and it. An **experiment** is the cheapest thing that clears one of those unknowns.

**A work item** is something already decided: a defect, a slice everyone has agreed on, a chore. Nothing has to be found out before it can start.

The test for which one you have is a single question: *is there anything here we would have to find out before we could start?* Nothing → a work item. Something real → an idea.

Keeping them apart is what lets an idea be honest about wanting something while an experiment stays honest about what it found. An objective is a goal: it does not come out true or false, and asking it to be falsifiable only produces a question nobody actually had. An unknown is the opposite: it is the thing that could go either way, and it is what an experiment is pointed at. A bug has neither, and pushing one through a shaping lifecycle produces states that mean nothing.

Like the rest of this folder, both kinds are **records rather than notes**, and both are exempt from the writing charter in [[the vault index]]. There is no mechanism-first rule here and no requirement that reasoning sit in callouts. What they keep is frontmatter, because that is what puts them in the tables below.

## An idea's life

```
ideas/                 zenku:capture-idea writes an objective in a few seconds
  → unknowns named      zenku:experiment names what stands in the way, and writes it back to the idea
  → experiments/        the unknowns this one goes after, and what a successful run would look like
  → a branch            one branch per idea: the spikes live there, never on main
  → conclusion          the same skill scores it and writes the answers back onto the idea
  ↺ repeat              unknowns left → another experiment, on the same branch, building on the last
  → decision            list empty → zenku:promote builds the real thing, or zenku:drop closes it out
```

**An idea outlives its experiments**, and everything else here follows from that. Four unknowns can take four experiments, each scored and concluded on its own, while the idea stays open the whole time. So an experiment never decides whether the thing gets built, and never throws anything away: its spike stays on the branch where the next experiment can start from it. The disposal happens once, at the end, when the idea is decided.

That decision is two decisions rather than one, and `zenku:promote` keeps them apart deliberately: whether the objective is still worth reaching now that the answers are in, and only then what shape the real thing takes.

## A work item's life

```
work/                  zenku:capture-backlog writes down what is already decided
  → doing              zenku:work-on-backlog agrees the shape, builds it, verifies it
  → reviewed           the change is reviewed for fit, then by the user, before anything is committed
  → done               what was actually done goes back onto the item
```

Shorter, because there is nothing to learn. Order comes from the `priority` field and the table below: **there is no separate ordering artifact and no planning document**. What is at the top is what gets picked up.

The two backlogs feed each other, and that is how "proven, now build the rest of it" works without a third artifact in between:

- A work item that turns out to carry a real unknown stops and becomes an idea.
- A promoted idea that leaves furniture behind (the follow-ups the build deliberately deferred) leaves it as work items.

## The four rules that hold this together

Four, and they are the only four.

**Acceptance criteria are written before the code.** What we would call a successful experiment goes in the note first, while it is still cheap to be honest about it. Decide it afterwards and it will be met, not through dishonesty, but because a result is much easier to admire once it is the only one you have.

A criterion does not have to be a number and does not have to be designed to fail. What it has to be is **observable**: something a person could point at and agree on without having been in the room. "It works well" is not a criterion. "The item exposes a timing window and text for every paragraph" is one, and it costs nothing to write.

**Every note reaches the trunk before any code is discarded.** Code lives on the idea's branch and is expected to be thrown away; the notes are not. They travel to the trunk with the decision, in `zenku:promote` or `zenku:drop`, which is the moment disposal happens and the last moment a missing note is recoverable.

**Promoting is not a cleanup.** No spike reaches the trunk. When an idea is promoted its spike commits are dropped and the real thing is built with the answers in hand. The permission to hardcode, skip tests and ignore structure is what made them cheap, and auditing it back out afterwards is slower and less reliable than writing it properly. Between discarding and building sits a conversation about the shape: what is actually being adopted, where it lives, and what the project's standing rules rule out. That conversation is the part that matters.

**What gets built is reviewed before it is committed.** Green checks say the code runs, not that it is the thing anyone wanted, and a change already committed is asking a different question than a change still sitting in the working tree. This applies to a work item exactly as much as to a promoted idea.

Experiment code is exempt from the quality bar and **not** from the project's standing rules: a spike that quietly breaks an invariant in [[invariants]] cannot be compared against anything.

## Naming and frontmatter

Everything here is named for its subject in kebab-case, like the rest of the vault, and names must be unique across it: wikilinks resolve by name. No dates and no numbers in file names: a date is a frontmatter field, which is what the tables sort on.

An **idea** carries `status`, `priority`, `impact` and `size`. The status is the whole lifecycle in one field:

| Status | What it means |
|---|---|
| `raw` | An objective, dropped in a sentence. We know what we want and nothing else. |
| `framed` | The objective is stated properly and we know what it would change. The unknowns are not enumerated yet. |
| `shaped` | The unknowns are named, and at least one could be cleared starting today. **This is what an experiment needs.** |
| `promoted` | The unknowns are cleared and it is worth having. It is built, being built, or the settled direction. |
| `dropped` | We are not doing it, whether the unknowns were cleared or the objective simply stopped being worth reaching. |

The other three are not about progress:

| Field | Values | What it means |
|---|---|---|
| `priority` | `next` · `soon` · `whenever` | Which of these we would pick up now. The values are chosen so the table sorts on them alphabetically without a formula. |
| `impact` | `high` · `medium` · `low` | How much *reaching the objective* changes. Not how much we want it. |
| `size` | `small` · `medium` · `large` | What reaching it would cost. Cheap and `high` impact is what you want to pick up next. |

An **experiment** carries `status`, `started`, `concluded` and the branch it ran on. Its statuses say what happened to the **unknowns it went after**, and nothing about whether the idea was any good: that verdict belongs to the idea, which is the thing that gets promoted:

- **`running`**: in flight, on its branch.
- **`cleared`**: met its acceptance criteria. The unknowns it went after have answers.
- **`partial`**: some cleared and some not, or the answer arrived from somewhere the criteria did not anticipate. Common, and not a failure.
- **`inconclusive`**: the criteria were not met and the unknowns are still open. An honest status rather than a euphemism, and a real result: it says this approach did not answer the question.

A **work item** carries `status` (`open` · `doing` · `done` · `dropped`), `priority`, `size` and `kind` (`defect` · `slice` · `chore`). An item that is only partly done stays `open` with what is left named. A `done` item that is not done is worse than an open one.

Ideas link their experiments and experiments link their ideas, both in frontmatter and in the `Related` footer. An idea note is never converted into an experiment note: the experiment is a new note, the idea stays where it is, and one idea commonly carries several.

Create each from `_templates/idea.md`, `_templates/experiment.md` or `_templates/work.md`.

## How we work

Anything learned about the *process* rather than about the product lands here, as a short subsection. That is deliberate: this file is the only place the way we work is written down, so a habit that lives in someone's head is a habit the next session does not have.

### Spikes are throwaway, one branch per idea

nagara ran its first three experiments under the opposite convention: **graduate-in-place**, spikes built directly in `api/` and `web/` and hardened where they landed, because the TTS pipeline's technical risk was already spent and a rewrite looked like wasted motion. It cost something the project's own record noticed: [[player-ready-item]]'s insight log says plainly that under graduate-in-place, the experiment "absorbed substantial production-hardening inside the timebox (pydantic-settings, module packages, `APIKeyHeader` auth on all routes, ~17 tests, ruff/ty, a dropped dependency)"; a signal that "spike" had come to mean near-production code, budgeted for accordingly rather than genuinely cheap. [[read-along-player-shape]] then deliberately broke from that convention on its own (an isolated throwaway Vite+React app) and turned in the most cleanly scoped of the three experiments, exercising a shape question without first committing the real stack.

The lab now runs throwaway spikes on `idea/<slug>`, discarded at promotion, and the real thing is built once the answers are in. This reverses the project's own original convention on the evidence of its own first experiment, not on the plugin's default.

### Pre-register a synthetic probe when the real artifact cannot reach a case

When the real work artifact cannot exercise a load-bearing disproof condition (a fixture that happens not to contain the hostile case, an article missing the construct a hypothesis hinges on), that condition is unfalsifiable as written, and a criterion that cannot fail proves nothing. Pre-register a **minimal synthetic probe** built to trigger exactly that case, and mark it explicitly as separate from the real-artifact judgment: the real data still owns the verdict; the probe only keeps the disproof honest. Say plainly what the probe covers (often strip- or transform-level only) and what stays deferred, so the scope does not silently narrow. Reach for this only when the real artifact genuinely cannot reach the case, never as a substitute for real data.

Learned in [[markdown-paragraph-pipeline]], where the clean-HTML fixture contained no code blocks or blockquotes and a mandatory synthetic snippet caught a blockquote-strip bug the real article never could.

### For a UI-shape question, explore several variants and recombine them

When the experiment is discovering the *shape* of a UI screen (layout, interaction, feel), default to **breadth-then-depth**: build several coherent whole-screen variants as cheap static mockups on real content, compare them side-by-side, then **recombine** (take the shell from one, the reading surface from another, fold a rejected idea back in as a mode), and only then wire the finalist to the real engine. Exploring and mixing ideas reliably lands a better shape than starting from a single design and iterating it, which hill-climbs a local optimum. Keep the variants ruthlessly static until one or two are chosen to wire; the felt, load-bearing behaviours are only judged once wired.

Learned in [[read-along-player-shape]], where four static archetypes recombined into a single player with two modes (a calm reader by default, an opt-in focus teleprompter), a shape neither archetype was on its own.

A live builder-driven discovery loop (builder edits, user judges the shape in real time) is high-yield for exactly this kind of question, but it is **oracle- and builder-confounded** by construction: it validates the shape, never demand or that a fresh user would experience it the same. Name that confound in the verdict; do not let a satisfying shape masquerade as validated demand.

## Every idea, ordered by priority

Every note tagged `idea`, ordered by priority. Generated, so a new idea appears by existing. **Backlog** is what is live; **Settled** is what has been promoted or dropped, kept out of the queue and one click away, because a built idea sorting above an unstarted one makes the queue unreadable.

Keep it short. A long backlog stops being a queue and becomes a place ideas go to be safe from ever being picked. Capturing is cheap enough that nothing is lost by writing an idea down the day it matters instead of hoarding a list of them.

![[ideas.base]]

## Every work item, ordered by priority

![[work.base]]

## Experiments

![[experiments.base]]

---

Related: [[the vault index]]
