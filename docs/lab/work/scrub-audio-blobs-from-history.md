---
title: "Scrub audio blobs from history"
tags:
  - work
summary: "Two Opus fixtures, 9.35 MB together, sat in already-pushed history; a filter-repo rewrite and a force push removed them and took .git from 12 MB to 672 KB."
status: done
kind: chore
priority: whenever
size: small
---

# Scrub audio blobs from history

## What

The commit concluding experiment 003 added two Opus audio fixtures under the read-along-player spike's tree: `experiments/003-read-along-player/spike/public/fowler.ogg` (6,957,270 bytes) and `mitchell.ogg` (2,386,188 bytes), 9.35 MB together. That commit was already pushed to `origin`, so deleting the files from the working tree would not have removed the blobs: they stay in history at full size until someone rewrites it.

So this was a history rewrite followed by a force push, not a plain deletion, and it touched every ref and every clone downstream of `origin`. `.gitattributes` routes `*.ogg`, `*.wav`, `*.mp3` and `*.png` through Git LFS, which stops the same thing recurring, and a rewrite is the only thing that removes a blob already committed without it.

Nothing irreplaceable was at stake either way: the audio is regenerable from the item pipeline at roughly $0.008 per article (see [[tts-service]]), so this was a repo-hygiene chore rather than a data-recovery one.

## Resolution

`git filter-repo --invert-paths` on the two `.ogg` paths, run after the vault migration landed on `main` so the rewrite covered the migration commit too. Every commit from the experiment-003 conclusion onward got a new hash; everything before it was untouched. `main`'s tree came out byte-identical to the pre-rewrite tree (`b2f7e63`), which is the check that the rewrite removed only the two blobs. `.git` fell from 12 MB to 672 KB, and `main` was force-pushed with a lease against the old tip.

> [!warning] The remote keeps unreachable objects for a while
> A force push makes the blobs unreachable on `origin` rather than deleting them; GitHub retains unreachable objects and still serves them by hash until its own garbage collection runs, which is not on a schedule anyone outside GitHub controls. For a public repository, treat anything once pushed as still fetchable by someone who recorded the hash. Nothing here was sensitive, so unreachable was the whole goal; a scrub of a leaked credential would need the key rotated rather than the history rewritten.

The spike audio is not carried onto the `idea/read-along-player` branch either, so the player spike there has its fixture JSON and no audio to play against until someone regenerates it.

---

Related: [[lab/README|the lab]] · [[deployment-and-ci]] · [[tts-service]]
