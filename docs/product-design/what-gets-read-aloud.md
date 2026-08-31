---
title: "What gets read aloud"
tags:
  - product-design
summary: "The article body, and nothing else: a code block and an image are each described in one spoken sentence, a table reads as prose, a link reads as its anchor text, and the author's own words are preferred wherever they exist."
---

# What gets read aloud

The product face of [[article-extraction]]: what a listener actually hears, independent of the markdown mechanism that produces it.

## Only the article body

Navigation labels, an echoed title, and content that carries no real words at all are all silently dropped before synthesis: a listener never hears "Table of Contents" read aloud, and never hears the article's own title spoken twice. Some boilerplate still gets through: a footer donation ask or a sponsor mention arrives as ordinary prose sentences and is not yet distinguished from real content; see [[prose-boilerplate-stripping]].

A footnote reference marker is dropped wherever the page marks it as one, which covers the superscript-wrapping-a-link shape nearly every publisher emits, Wikipedia's bracketed reference and Substack's footnote anchor: a listener hears "in a loop, at a bare minimum" rather than "in a loop one at a bare minimum". A `[1]` typed into the prose as ordinary text carries no markup to recognize it by, so it stays and is read aloud. The marker leaves the page along with the audio, because the extraction drops the footnote section's anchors and a marker pointing at nothing is not a link a reader can follow. The footnote's own text is kept either way, and reads as a sentence of its own at the end of the article.

## Non-prose constructs read as something sensible, not as syntax

- **Emphasis, links, and headings** read as their plain words: a link says its anchor text, never the URL underneath it.
- **A list item** reads as its own sentence, marker dropped.
- **A blockquote** reads as clean prose, quote marks dropped.
- **A code block** is described in one spoken sentence rather than read aloud: the listener hears what kind of code it is and what it is for, announced with a spoken `Code:` cue ("Code: A Python variable definition."). The source is never read back, and the sentence never claims what the code does. When no description can be made, the listener hears a short honest line ("Code with no description.") rather than silence.
- **An XML-like tagged word** an author wrote about (`<software>`, `<your-api-key>`, `<T>`) reads as the words inside it, brackets dropped, so the listener hears "software" and "your API key". A reader still sees the brackets on the page, because they are the author's own notation for a placeholder or a generic.
- **A table** reads as header-aware prose ("Feature: Extraction, Status: done.") rather than speaking pipe characters.
- **An image** is described in the author's own words when there are any, and otherwise in one generated sentence of what it shows. In order of preference the listener hears: the author's caption, verbatim; else the author's alt text, when it is a real sentence; else one generated sentence of what the image shows, announced with an `Image:` cue; else any alt there is; else an honest "Image with no description." rather than silence.

## The author's words win, and a description only makes an image visible

Both a code sentence and an image description are generated, so a very code- or image-heavy article carries a budget: only so many descriptions are made. The descriptions go to the blocks that come first in reading order; past the budget a code block falls to its honest short line, and an image falls down its precedence to alt or to the floor. The article still plays start to finish, never failed or silenced for being over budget.

> [!note] A description makes an image visible, it never says what it means
> Meaning comes only from the author, so a caption or a real alt sentence always wins where it exists. A generated sentence says what is shown, the decaying fish on the sand, the axes of a chart, and stops there: it makes the image visible without reading anything into it.

> [!note] A code sentence earns its own moment even when the prose just introduced it
> A tutorial usually names a block in the sentence right before it, so the spoken description often restates what the listener just heard. It is generated anyway: dropping it would take the code off the page for the reader too, which in a tutorial is a real loss, so the block keeps both its window in the audio and its place on the page.

> [!note] A flawed alt is spoken only when a description could not be made
> Alt that is a subscribe prompt, keyword soup, or a bare filename is what sends an image to a generated description in the first place, so it is never spoken on the normal path. It returns only as a last resort, when the description itself could not be produced, because a clumsy line that says an image is there still beats silence that hides it.

> [!warning] What a listener hears and what a reader sees can be surfaced markdown, never plain prose
> The player renders the same markdown a listener's ears never hear directly: it is the strip that keeps the audio clean, not a separate "reading mode" of the text. A change to what gets read aloud is a change to [[article-extraction]]'s strip, and needs a fixture, per `CLAUDE.md`'s recipe for adding an extraction rule.

## What is not built yet

A bare comparison operator is silent: `3 < 4` reads as "three, four", because the character is left as the author wrote it and the voice has no word for it. Speaking one aloud is a reading rule of its own and nothing in the corpus asks for it yet.

Speaking a quote in a distinct voice from the narration ([[quote-voice-switching]]); adjustable playback speed ([[playback-speed-control]]).

---

Related: [[article-extraction]] · [[listening-experience]] · [[item-contract]] · [[prose-boilerplate-stripping]]
