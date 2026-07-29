---
title: "Auth"
tags:
  - work
summary: "Google OAuth login plus the pasted-URL-survives-redirect stash/replay, replacing the single-user API-key shim for the public-funnel cluster."
status: open
kind: slice
priority: soon
size: large
---

# Auth

## What

Google OAuth login, plus stashing a pasted URL through the login redirect and replaying it afterward so a stranger's first action on the [[landing]] page is not lost. Replaces the single-API-key shim described in [[authentication]] for the public-funnel path; see that note's "what is not built yet": multi-user is a real replacement, not an extension of the single-key model.

Fourth of six in the build order agreed 2026-07-17, and the first of the **public-funnel cluster** (real auth and onboarding), built in service of [[validate-demand]].

---

Related: [[lab/README|the lab]] · [[landing]] · [[authentication]] · [[validate-demand]]
