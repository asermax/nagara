---
title: "Richer extraction notes"
tags:
  - quest
summary: "Write the durable notes once, out of every slice at once, and strike the two spike worktrees the adventure has been living in."
status: open
kind: build
adventure: richer-extraction
blocked_by:
  - richer-extraction-listen-pass
priority: 3-later
created: "2026-08-02"
---

# Richer extraction notes

## What

The last quest in [[richer-extraction]]. Everything is built and heard, so it can be described in the present tense.

Per [[quest-log/README|the quest log]], the durable note is written at the very end out of every quest's design at once, and no quest writes one on the way there. A page per slice describes parts of a shape nobody has seen whole, and reconciling those afterwards costs more than writing it once.

Two exceptions already landed, because `CLAUDE.md` requires the invariant list and its explanation to change together or they drift: invariants 1 and 2 shipped with [[typed-unit-contract]] and invariant 5 shipped with [[queued-item-lifecycle]]. This quest checks they still say what the built code does, and writes everything else.

## Design

### The notes

| Note | What changes |
|---|---|
| [[item-contract]] | the typed `Unit`, the `units[]` wire shape with no `spoken`, the retry route, `queued` in the status vocabulary, the image route. **Replace** the "why the field is still called `text`" callout rather than editing it |
| [[article-extraction]] | the fallback fetch and the escalation trigger, the two fence rules, the boundary repair, image selection and captions, the describer, and the invariant-1 callout: `spoken` persists on the unit and is filtered at the response boundary |
| [[item-lifecycle]] | the four-state machine, the five-minute ceiling, the retry route, the six error prefixes, and the hard-against-degraded line. Its three existing callouts get **real answers, not deletion** |
| [[persistence-and-storage]] | the shared storage base, the content-hash key, the read-time-mint route, the half-configured inheritance, the `degradations` column, the `cost_entries` table |
| `docs/product-design/` | what a listener hears for an image and for a code block, which is a statement about experience rather than mechanism |
| [[invariants]] and `CLAUDE.md` | verify 1, 2 and 5 match the built code; the two files must not disagree |

Per the vault charter: mechanism first, reasoning in a callout beside the thing it justifies, mermaid wherever the subject has a shape, and no reprinted code.

### Three quests to resolve

[[reach-guarded-pages]] is **answered outright** by the fallback fetch, at 5x an ordinary article's price and 30x for an X URL, not at parity.

[[image-extraction-and-alt-text]] **becomes this adventure's image half** and its framing changes. The spoken form is caption, then good alt, then a generated sentence, then a fallback, rather than "speak the alt text" as originally framed.

[[trustworthy-extraction]] is **not consumed** and stays open. It sits adjacent and this adventure handed it the first real evidence it has ever had: no shape-based plausibility test separates the corpus. Median unit length does not separate, since a degraded extraction sits at 12 between a legitimate 11 and a legitimate 16, and neither does link density. Only total word count separates, and only because the corpus contains no genuinely short article. Write that into it.

### Two housekeeping fixes worth doing here

**`CLAUDE.md` still describes a vault layout that no longer exists.** Commit `0a57c99` migrated `docs/lab/` to `docs/quest-log/` and merged ideas and work into one quest list, and `CLAUDE.md` still points at `docs/lab/ideas/`, `docs/lab/experiments/`, `docs/lab/work/` and `docs/lab/README.md`. This quest touches `CLAUDE.md` anyway.

**`api/.env.example` does not exist** and is owed by this build, covering every setting rather than only the new ones.

### Then strike the worktrees

Two spike branches carried this adventure's evidence and are never merged: `idea/firecrawl-markdown-fidelity` (the corpus cache, the cost model, the bake-off, the image and boundary prototypes) and `idea/describer-prompt-design` (the prompt variants and the listen clips).

> [!warning] This is the last moment anything on them is recoverable
> Strike them **after** the notes are written and never before. Anything that mattered has to be in a note or in a solved quest by then.

`idea/firecrawl-as-the-extractor` is a separate experiment and not this adventure's. Leave it alone.

The gitignored `.scratch/richer-extraction/` tree goes the same way, and for the same reason: nothing in it is a project record.

### What stays open on purpose

Six things, recorded in the adventure's own notes and not resolved here: the caption-export surface, whether a table deserves its own unit variant, the X-destination multiplier as an [[api-hardening]] signal, a corpus entry that would actually test the 250-word floor, whether claiming to be a browser is a decision anyone else gets a say in, and whether a high rate of fenced-prose re-classification should escalate at the document level.

Two of them are sharp enough to be quests. Neither is one yet, and both may belong to a fresh adventure rather than this one.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[item-contract]] · [[article-extraction]] · [[item-lifecycle]] · [[persistence-and-storage]] · [[invariants]] · [[reach-guarded-pages]] · [[image-extraction-and-alt-text]] · [[trustworthy-extraction]]
