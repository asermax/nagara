---
title: "Single-origin web and API"
tags:
  - idea
summary: "Serve the web frontend and the API from one origin instead of separate hosts, so the future player gets no CORS and a clean presigned-audio flow."
status: shaped
priority: soon
impact: medium
size: medium
experiments:
---

# Single-origin web and API

## Objective

Serve the web frontend and the API from a single origin (for example `nagara.asermax.com`) instead of separate hosts. Railway maps a domain to one service, so one surface must own the domain and route to the other over private networking. Same-origin buys no CORS and a simpler cookie/session story for the future player's auth, plus a clean presigned-audio flow. Do this when the web frontend lands, not before.

## Unknowns

- Which surface owns the domain and proxies to the other? The preferred shape is the TanStack Start server owning the domain and proxying `/api/*` to the API service over `nagara-api.railway.internal:8080`; the alternatives are a dedicated reverse-proxy service or a Cloudflare Worker doing path routing. This is a single experiment's worth of comparison once there is a `web/` to route to.

---

Related: [[lab/README|the lab]] · [[deployment-and-ci]] · [[authentication]]
