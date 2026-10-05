---
name: vault-sync
description: Syncs nagara's state between this repo plus its Linear project and the nagara notes in the shin-sekai Obsidian vault (../shin-sekai), in both directions. Pulls the vault, reads what changed on each side since the last sync, proposes the updates both ways, and applies only what the user approves. Use when the user asks to sync the vault, update the nagara project notes, or check the vault for new nagara ideas.
---

# Sync nagara with the shin-sekai vault

The vault at `../shin-sekai` (from the repo root: `~/workspace/asermax/shin-sekai`) holds nagara's project notes and the captures, weekly objectives and research that mention it. The repo and Linear hold what was built and what is planned. The two drift apart between syncs, and each side has things the other lacks: the vault falls behind on what shipped, and Linear misses ideas that were only captured in the vault.

The session has three steps, in order: gather, propose, apply. Nothing is written on either side before the user approves the proposal.

## 1. Gather

### The vault

Run `git pull` in the vault first; the vault's own `CLAUDE.md` requires it. Note any untracked files `git status` shows, so they are never swept into a commit later.

The nagara notes:

| Note | What it holds | What goes stale |
|---|---|---|
| `01_Projects/nagara/index.md` | The project overview. The status paragraph, `## Repo state (synced YYYY-MM-DD)` with the commit `main` was at, "Built", "Not built", the Linear backlog by milestone, and conventions | Everything above the "Turn Tachikoma's…" paragraph |
| `01_Projects/nagara/mvp.md` | The original July MVP spec | Only its top note, which links to `index#Repo state (synced YYYY-MM-DD)` |
| `02_Areas/Ideas/nagara.md` | The ideas-garden mirror: weekly objectives with their outcomes in italics, and agreed next steps | The outcome of the latest weekly objective, and the next step |
| Every other note under `01_Projects/nagara/`, subfolders included | Whatever the folder has gathered: research, designs, specs, reference material, new topics | List the folder each sync, because notes get added. A note added since the last sync is a candidate for the Linear side; an older note goes stale when the repo has since changed what it describes |
| `04_Archive/*nagara*` | Captures already processed into Linear | Never; read-only |

The last sync date is the `last-iterated` field in `index.md` and the date in its `Repo state` heading. Find everything that touched nagara since then:

- `git log --since=<last sync> --name-only` in the vault, filtered to files that mention nagara.
- `grep -rli nagara 00_Inbox 02_Areas 03_Resources 01_Projects`, then read the matching lines (`grep -n -B2 -A6`) of the files changed since the last sync. The usual sources are daily-note captures and reflections, weekly plans, inbox notes and research notes.

### The repo and Linear

- `git log --since=<last sync> --format='%h %ad %s' --date=short` on `main`, skipping `test`, `refactor` and `style` commits for the overview. Note the current `main` commit for the `Repo state` heading.
- Linear project **nagara** (team Asermax): every milestone with its progress and description, and every issue with status, milestone and labels.

## 2. Propose

Compare the two sides and propose updates in two groups.

**Vault ← repo and Linear.** Usually the larger group:

- `index.md`: the status paragraph, the `Repo state` section (commit, deployables, what was built since the last sync), and the backlog: closed milestones with what they delivered, open milestones with their issue ranges and one line each, loose issues.
- `mvp.md`: the anchor in its top note, which must match the new `Repo state` heading exactly or the link breaks.
- `Ideas/nagara.md`: the outcome of the latest weekly objective, and the next step.
- Any other link into `index.md` whose anchor carries a date.

**Linear ← vault.** Ideas, captures or research about nagara that have no Linear home yet. For each one, propose a home: an issue in an existing milestone, a loose issue, or a new milestone. Check the existing issues first, because most vault ideas already have one. Follow the work tracking rules in the repo's `CLAUDE.md`. In particular, a new milestone's description says it is to be shaped and designed before tasks are written.

Present both groups with the reason for each item, and stop. The user often excludes items. Daily-note captures, weekly plans and research notes under `03_Resources/` are the user's own records, so propose a change to them, never make one silently.

## 3. Apply

Apply only the approved items.

- **Vault edits.** Read each note before editing it. When updating `index.md`, change `last-iterated`, the `Repo state` heading date and the `mvp.md` anchor together, so the link keeps resolving. Keep the notes' existing shape: `index.md`'s sections, the italic outcome after a weekly objective.
- **Vault commit.** Stage only the files you edited, by path, never `git add .`, because the vault carries untracked folders that are not yours. Commit with `docs(nagara): sync repo state YYYY-MM-DD` and push, which is the vault's convention. Check `git log -1 --stat` to confirm every intended file is in the commit; an edit that failed silently leaves a file out.
- **Linear.** Create or move the approved milestones and issues. Linear has no done state for a milestone: it completes when all its issues are done or canceled.

End with what changed on each side, the vault commit hashes, and anything left out because the user excluded it.
