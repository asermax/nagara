---
title: "{{title}}"
tags:
  - idea
summary: "One line: the objective, stated as something we want to be able to do. Shown in the backlog table and in search."
status: raw
priority: whenever
impact: medium
size: medium
experiments:
---

# {{title}}

## Objective

What we want to be able to do, and what it looks like when we can. An objective is a goal rather than a question: it does not come out true or false, and nothing here has to be falsifiable. That job belongs to the experiments.

State it so that it carries its own justification: an objective says what we cannot do today, and that is the whole of why it matters. There is deliberately no section arguing for the idea: one that needs a paragraph of advocacy has not been stated plainly enough, and the space invites the note to grow apparatus nobody asked for.

Constraints belong here too, since a condition attached to one thing we want is not a second idea. So does anything already settled or already true of the code (a decision taken elsewhere, a handle that already exists), so that nobody re-tests it or mistakes it for an unknown.

## Unknowns

What stands between us and the objective. One per bullet, each one something a single experiment could clear, and each one phrased so that clearing it has an outcome someone could point at.

A cleared unknown is struck through and answered in place, so the list reads as a history rather than a to-do:

```markdown
- ~~Does a plain HTTP fetch handle a JS-rendered article?~~ → **Yes**, it server-renders. [[some-experiment]]
- Still open, and nobody has tried it yet.
```

This is the list the experiments work through. The idea stays open until it is empty, or until the answers make the objective not worth reaching, which is a perfectly good ending. Leave this section out while the idea is still `raw` or `framed`: writing it is what makes the idea `shaped`, and `shaped` is what an experiment needs.

## Conclusion

Left out until there is one. This is where the idea ends: what was decided and on what evidence, written by `zenku:promote` or `zenku:drop`, and by nothing else.

A promoted idea says what was actually built and where it now lives, which is rarely the shape any experiment used. A dropped one says which kind of drop it was and, most valuably, **what would reopen it**: that line is the difference between an idea that stays closed and one that gets re-argued every few months.

---

Related: [[lab/README|the lab]]
