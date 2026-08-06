---
title: "Plain fetch hardening"
tags:
  - quest
summary: "A browser user agent and a status check stop an HTTP 403 reaching ready and synthesizing, and cassettes arrive so the suite can prove both."
status: solved
kind: build
adventure: richer-extraction
blocked_by: []
priority: 2-soon
created: "2026-08-02"
---

# Plain fetch hardening

## What

Enqueue `mitchellh.com` today and nagara synthesizes an error page. The plain fetch sends trafilatura's default user agent, that host answers it with HTTP 403, and nothing reads `response.status`. The 403 body arrives with 31,074 bytes, passes the emptiness check, passes the content-type gate, extracts to eight words, yields two units, passes `if not display`, and reaches `ready`.

Two fixes, both free, and together they account for most of what the firecrawl fallback was written to chase. After this quest that URL either succeeds with a browser agent or fails honestly with `fetch:`.

This quest also brings in the cassette infrastructure, because the two fixes are exactly what a module-boundary mock cannot verify and everything after this depends on the same setup.

## Design

### The two fixes

**Send a browser user agent.** Re-fetching the whole corpus both ways, the browser agent fixes exactly the `mitchellh.com` entry and changes nothing else. That article is the one the repo trusts, the committed fixture, and the only URL to come through the end-to-end push that de-risked the spine unchanged.

**Read `response.status`.** `extract_article` checks `response is None or not response.data` and nothing else. A non-2xx is a free, unambiguous, protocol-level signal sitting unread.

> [!note] This is the [[trustworthy-extraction]] failure mode arriving through the front door
> Not an exotic 200-status error page. An ordinary 403 that nothing looks at.

### The error prefix vocabulary settles here

Six prefixes, with `fetch:` split out of `extraction:` rather than added beside it. The split is transport against interpretation.

| Prefix | Phase | Hard when |
|---|---|---|
| `fetch:` | getting the document: plain fetch, content-type gate, decode | non-HTML content type, connection or status error |
| `extraction:` | trafilatura turning fetched HTML into units | no article text, no units surviving |
| `spawn:` | spawning synthesis | unchanged |
| `store:` | storing audio and timing | unchanged |
| `tts:` | remote synthesis | unchanged |

`enrichment:` is the sixth and arrives with [[queued-item-lifecycle]]. The prefix is the first word of a free-text string rather than an enum: a machine-readable failure taxonomy would be furniture nobody has asked for.

`ExtractionError` stays and is scoped to acquisition. Fetch and extraction raise from the same pipeline, are caught at one site, and recover identically on retry, so the `fetch:` against `extraction:` distinction is carried by where the raise happens. A `FetchError` subclass or a phase attribute is build style, not a contract decision.

The content-type gate keeps reading the plain fetch's own headers and keeps raising. A PDF is a clean failure.

### Cassettes, and why they arrive with this quest

A module-boundary mock (`@patch("...trafilatura.fetch_response")`) replaces the function wholesale, so it **structurally cannot** verify that the browser agent is sent or that the status is read. A cassette records the request headers and the response status, so both run against the real `fetch_response`.

`vcrpy` behind `pytest-recording`, as dev dependencies. Four configurations, each a one-liner and each non-obvious enough to name:

**`filter_headers=["authorization", "x-api-key"]` in one session-scoped `vcr_config` fixture.** vcrpy records credentials into the committed YAML unless told not to, and scrubbing is opt-in rather than default. Centralizing it means there is no per-test opt-in to forget and the only way to leak is to edit that one fixture, which is a visible diff. This repository has already had to clean a leaked key out of its history once.

**`match_on` must include `body`.** vcrpy matches on method, scheme, host, port, path and query by default. Firecrawl and the describer are each one endpoint called with a different body per item, so URL-and-method matching collapses every article onto one cassette entry and replays the first recorded response for all of them. This is the gotcha most likely to be forgotten, because it is invisible until two tests silently share an entry.

**`--block-network` in the CI pytest invocation.** A bare `pytest` is replay-only at record mode `none`, needs no keys, and never touches the network. `--block-network` turns a missing cassette into a red test rather than a hidden network call.

**Re-recording is local only.** `pytest --record-mode=rewrite path::name` rewrites one cassette; `--record-mode=once` records only what is missing. Both need keys. CI never records.

> [!warning] `pycurl` must stay out of the dependency tree
> `trafilatura.fetch_response` routes through urllib3, which vcrpy records. Installing pycurl silently reroutes it through a C extension vcrpy cannot see, and cassettes would break without failing informatively. `HAS_PYCURL` is false in the venv today.

One thing to confirm on the first recording: trafilatura streams with `preload_content=False` and `response.stream()`, which no cassette here has exercised yet.

### The complementary split, not either-or

Committed fixtures stay the input for extraction-logic tests, which is the bulk of `test_extract.py`. Cassettes are for fetch-contract tests: the user agent is sent, the status is read, and later the escalation trigger driven by a recorded non-2xx. The tradeoff is readability, because article HTML in a YAML envelope is worse to edit than a committed `.html`.

Invariant 6 holds. A cassette patches the transport at test time and touches no runtime code, which is structurally identical to the `@patch` the suite already does, one layer lower.

## Answer

Built. A browser user agent goes out on every plain fetch, and a non-2xx response raises `fetch: HTTP {status}` before the empty-body check, so a 403 fails the item instead of extracting cleanly and reaching `ready`.

**How far it reaches.** Two cassettes in `api/tests/cassettes/test_fetch_contract/` record the real exchanges: one asserts the user agent actually leaves the process, the other that a non-2xx raises. The user agent is the assertion, which is why it is the one header the cassettes keep.

**What would make it stop being true.** This closes only the case where the *protocol* says the fetch failed. A 200-status error page still extracts cleanly, still synthesizes, and still reaches `ready`; that is [[trustworthy-extraction]]'s and is untouched here.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[article-extraction]] · [[trustworthy-extraction]] · [[firecrawl-fallback-fetch]]
