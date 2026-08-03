---
title: "{{title}}"
tags:
  - adventure
summary: "One line: what this adventure is for. Shows up in the quest log index."
status: open
kind: journey
priority: 2-soon
created: "{{date:YYYY-MM-DD}}"
---

# {{title}}

> `kind` is `journey` or `raid`, and it decides what belongs in here. A **journey** clears ground: its destination is knowing how to build the thing, and it holds research, design and spike quests, never a build quest. A **raid** builds: its destination is the thing working, it holds build quests, and its trials are normally empty because a journey already cleared them. Always state it: both index views query this field positively, so a record with no `kind` lands in neither and shows up nowhere — that absence is how you find it. Delete this quote when creating an adventure.

## Destination

What reaching the end of this looks like, in a line or two. Every session reads this before choosing a quest, and it is what makes something out of scope rather than a trial.

On a raid, name the journey it came from here or in the bearings. Its solved quests are where the reasoning behind every decision lives, and nothing was copied across.

## Bearings

What a session needs to know before it decides anything here. Three things, each a line or two:

**The ground.** Which part of the system this adventure is working in, and which parts it explicitly is not touching.

**Read first.** The notes and files to have read before deciding anything, named so nobody has to guess which ones matter.

**Standing preferences.** How this effort wants its decisions made, including the warnings: a branch that looks related and is not, a tempting approach already ruled out elsewhere, a tool this project will not take on. A negative bearing is the most valuable line here, because nothing else in the vault will contradict a wrong assumption before it costs a session.

## Trials

The ordeals you can sense standing between here and the destination but cannot yet phrase as a single quest. Write each as loosely as the view allows.

A trial leaves this list the moment it can be stated precisely, and becomes a quest of its own. It is coarser than a quest on purpose: one trial may graduate into several, or into none.

**A raid normally has none.** A trial appearing on one means the ground was not clear after all, and it belongs back in a journey rather than being guessed at mid-build.

## Solved

One line per solved quest, oldest first: the link, what it settled, which part of the shape it fixed, and anything it left behind that someone may need to open. Enough to judge whether it matters and to go and look, without opening the quest itself.

- [[a-solved-quest]] — what it settled, in a line. Which part of the shape that fixes. What it left behind, and where.

**This index points, it does not restate.** A decision lives in exactly one place, the quest that settled it, so nothing here repeats a quest's reasoning and no section of this note accumulates the design. Which is why the line has to say enough to choose by: a session picking up work reads these lines, not sixteen quest bodies.

## Out of scope

Ruled beyond the destination, with why. This never graduates: if the destination is redrawn, that is a new adventure, not a resumption.

## Outcome

**Delete this whole section, heading included, when creating an adventure.** It gets written when the adventure ends, whichever way it ended.

---

Related: [[quest-log/README|the quest log]]
