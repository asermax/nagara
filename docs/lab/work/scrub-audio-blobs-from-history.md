---
title: "Scrub audio blobs from history"
tags:
  - work
summary: "Two Opus fixtures committed to the spike, 9.35 MB together, sit in already-pushed history and need a history rewrite plus a force push to remove, not a deletion."
status: open
kind: chore
priority: whenever
size: small
---

# Scrub audio blobs from history

## What

Commit `1bdd17a` added two Opus audio fixtures under the read-along-player spike's tree: `experiments/003-read-along-player/spike/public/fowler.ogg` (6,957,270 bytes) and `mitchell.ogg` (2,386,188 bytes), 9.35 MB together. That commit is already pushed to `origin`, so deleting the files from the working tree does not remove the blobs: they stay in history at full size until someone rewrites it.

This is a history rewrite (`git filter-repo` or equivalent) followed by a force push, not a plain deletion, and it touches every ref and every clone downstream of `origin`. `.gitattributes` already routes `*.ogg`, `*.wav`, `*.mp3` and `*.png` through Git LFS, which stops this from recurring, but it does not retro-fix blobs committed before that file existed.

Nothing irreplaceable is lost either way: the audio is regenerable from the item pipeline at roughly $0.008 per article (see [[tts-service]]), so the scrub is a repo-hygiene chore, not a data-recovery one. Agreed with the user to do this once the current migration work is done, not before.

---

Related: [[lab/README|the lab]] · [[deployment-and-ci]] · [[tts-service]]
