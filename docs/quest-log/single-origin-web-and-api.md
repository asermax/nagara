---
title: "Single-origin web and API"
tags:
  - quest
summary: "Serve the web frontend and the API from one origin instead of separate hosts, so the future player gets no CORS and a clean presigned-audio flow."
status: open
type: design
adventure:
blocked_by: []
priority: 2-soon
created: "2026-07-17"
---

# Single-origin web and API

## What

Serve the web frontend and the API from a single origin (for example `nagara.asermax.com`) instead of separate hosts. Railway maps a domain to one service, so one surface must own the domain and route to the other over private networking. Same-origin buys no CORS and a simpler cookie/session story for the future player's auth, plus a clean presigned-audio flow. Do this when the web frontend lands, not before.

The shape question this settles: which surface owns the domain and proxies to the other? The preferred shape is the TanStack Start server owning the domain and proxying `/api/*` to the API service over `nagara-api.railway.internal:8080`; the alternatives are a dedicated reverse-proxy service or a Cloudflare Worker doing path routing. This is one session's worth of comparison once there is a `web/` to route to.

---

Related: [[quest-log/README|the quest log]] · [[deployment-and-ci]] · [[authentication]]
