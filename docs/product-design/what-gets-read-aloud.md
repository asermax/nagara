---
title: "What gets read aloud"
tags:
  - product-design
summary: "The article body, and nothing else: code reads as a short placeholder, a table reads as prose, a link reads as its anchor text, and an image is silently skipped rather than mis-spoken."
---

# What gets read aloud

The product face of [[article-extraction]]: what a listener actually hears, independent of the markdown mechanism that produces it.

## Only the article body

Navigation labels, an echoed title, footnote markers, and content that carries no real words at all are all silently dropped before synthesis: a listener never hears "Table of Contents" read aloud, and never hears the article's own title spoken twice. Some boilerplate still gets through: a footer donation ask or a sponsor mention arrives as ordinary prose sentences and is not yet distinguished from real content; see [[prose-boilerplate-stripping]].

## Non-prose constructs read as something sensible, not as syntax

- **Emphasis, links, and headings** read as their plain words: a link says its anchor text, never the URL underneath it.
- **A list item** reads as its own sentence, marker dropped.
- **A blockquote** reads as clean prose, quote marks dropped.
- **A code block** reads as a short fixed placeholder ("Code sample.") rather than the code itself: reading source code aloud is noise, not signal. The right long-term treatment (an LLM-produced short explanation of what the code does, say) is still an open idea.
- **A table** reads as header-aware prose ("Feature: Extraction, Status: done.") rather than speaking pipe characters.
- **An image** is silently skipped: an image-only unit strips to no spoken words and is dropped entirely, so a listener currently hears nothing where a reader would see a picture. See [[image-extraction-and-alt-text]] for carrying its alt text instead.

> [!warning] What a listener hears and what a reader sees can be surfaced markdown, never plain prose
> The player renders the same markdown a listener's ears never hear directly: it is the strip that keeps the audio clean, not a separate "reading mode" of the text. A change to what gets read aloud is a change to [[article-extraction]]'s strip, and needs a fixture, per `CLAUDE.md`'s recipe for adding an extraction rule.

## What is not built yet

Speaking a quote in a distinct voice from the narration ([[quote-voice-switching]]); adjustable playback speed ([[playback-speed-control]]).

---

Related: [[article-extraction]] · [[listening-experience]] · [[item-contract]] · [[prose-boilerplate-stripping]]
