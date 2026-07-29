---
title: "{{title}}"
tags:
  - work
summary: "One line: what needs doing. Shown in the work table and in search."
status: open
kind: defect
priority: soon
size: small
---

# {{title}}

## What

For a **defect**: what happens, how to reproduce it, and what should happen instead. The reproduction is the whole value of writing a bug down: a bug nobody can reproduce is a bug nobody will fix. Keep it to what was actually observed; a theory about the cause belongs below, marked as one.

For a **slice** or a **chore**: what gets built, and anything already agreed about it (an ordering, a dependency, a decision taken in a conversation on a date). That last part is what evaporates if it is not written down.

If this needs something found out before it can start, it is not a work item. It is an objective with an unknown, and it belongs in the idea backlog.

## Resolution

Left out until the work is done. What was actually done, where it landed, and which notes moved.

Where the fix differed from what this item proposed, say so: the item was a guess made before anyone looked, and the difference is usually the interesting part.

If only some of it got done, this item stays `open` with what is left named here. A `done` item that is not done is worse than an open one.

---

Related: [[lab/README|the lab]]
