# ADR-004 — Server-side extraction with trafilatura; headless browser deferred

**Status**: Accepted **Date**: 2026-07-17 **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md)

## Context

The pipeline must turn a public article URL into clean, trustworthy paragraphs — paragraph boundaries are the product's responsibility, since they drive the read-along highlighting. The feared hard case was JavaScript-rendered pages (e.g. Substack), which a plain HTTP fetch might return as an empty shell, seemingly forcing a headless browser into the pipeline.

Testing against real reading-list articles (a clean blog, a magazine longread, a newsletter, a JS-heavy Substack post, and a PDF) showed a plain fetch handled **every** HTML case, including the Substack post — it server-renders its content. The HTML-vs-headless boundary sits considerably further out than assumed.

## Decision

We extract **server-side with a plain HTTP fetch plus trafilatura** — fetch the URL, gate on the response content-type, extract the main article text, and read the title from the document metadata. Extraction owns paragraph segmentation and trims edge cruft (echoed title, navigation labels, footnote glyphs, punctuation-only lines).

**A headless browser is not part of the pipeline.** It is reached for only if a specific site actually fails, not preemptively. **Non-HTML content-types clean-fail** at enqueue with a clear error rather than being force-parsed into garbage.

## Consequences

- **Cheap and simple**: no browser runtime to install, run, or scale; extraction is a fetch plus a parse.
- **Non-HTML fails fast and clearly** (e.g. a PDF URL is rejected at enqueue), instead of producing a broken item.
- Extraction quality is good on typical public HTML, but **prose-boilerplate stripping is still crude** — footer/donation/sponsor asides that arrive as full sentences are left in, because a generic filter risks over-trimming real content. A smarter pass is backlogged.
- A genuinely client-rendered site (one that does *not* server-render) would still return an empty shell; handling it means adopting the deferred headless escalation for that case.

## Alternatives considered and not chosen

- **A headless browser (e.g. Playwright) up front** — not chosen: the evidence shows it is unnecessary for typical public articles, and it would add a heavy runtime to every extraction for a case that rarely arises.
- **A readability-style extractor** — not chosen: trafilatura produced trustworthy boundaries and titles on the real fixtures and also supplies the content-type needed for the non-HTML clean-fail in one fetch.
