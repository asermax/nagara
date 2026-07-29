# Read-along player spike

This tree is the spike from the [read-along player shape](../docs/lab/experiments/read-along-player-shape.md) experiment, relocated from `experiments/003-read-along-player/spike/` to `web/` so it sits where the real web surface will be built. It exists on the `idea/read-along-player` branch only; `main` carries no `web/` tree.

It is not production code and is not the starting point for one. Under this project's spike model a concluded spike is thrown away and the real thing is written from the answers it produced, so treat these files as evidence of what was tried rather than as a codebase to harden. What the experiment settled, and what it left open, is in the experiment note above and in the [read-along player](../docs/lab/ideas/read-along-player.md) idea.

## Running it

```
pnpm install && pnpm dev
```

`src/App.tsx` switches between the six whole-screen mockups and the two player runs. The player renders paragraph timings from `src/fixtures/`, which hold real pipeline output for two articles: *Micro Frontends* (172 paragraphs, 40 minutes) and *My AI Adoption Journey* (55 paragraphs, 14 minutes).

## The audio is not in the repository

`App.tsx` points the two player runs at `/fowler.ogg` and `/mitchell.ogg`, and no `public/` directory ships with this tree. Audio is deliberately excluded from the repository rather than stored in Git LFS, because every audio file here is pipeline output that regenerates for fractions of a cent; see [what binaries the repository accepts](../docs/technical-design/deployment-and-ci.md).

So the highlight and the scrub work on load, and playback has nothing to play. To restore it, enqueue the two articles through the API, download each item's audio as `web/public/fowler.ogg` and `web/public/mitchell.ogg`, and confirm the durations match the `duration` field in the matching fixture. Timings are keyed to a specific synthesis run, so audio generated with a different voice will drift out of sync with the fixture it is paired with.
