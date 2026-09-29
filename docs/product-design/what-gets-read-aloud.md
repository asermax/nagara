---
title: "What gets read aloud"
summary: "The article body, and nothing else: a code block and an image are each described in one spoken sentence, a table reads as prose, a link reads as its anchor text, and the author's own words are preferred wherever they exist."
created: "2026-07-29"
---

# What gets read aloud

## 🔭 Overview

What a listener hears, independent of the markdown mechanism in [article-extraction](../technical-design/article-extraction.md) that produces it.

## 📰 Only the article body

A listener never hears a navigation label or the article's own title read as part of the article, and a paragraph with no real words, such as a section-break ornament, is silently dropped before synthesis. Some boilerplate still gets through: a footer donation ask or a sponsor mention arrives as ordinary prose sentences and nothing yet tells it apart from real content.

Footnotes are left out of both the page and the audio: neither the reference markers nor the footnote text is read, so a listener hears "in a loop, at a bare minimum" rather than "in a loop one at a bare minimum".

## 🔣 How non-prose constructs are read

- **Emphasis, links, and headings** read as their plain words: a link says its anchor text, never the URL underneath it.
- **A list item** reads as its own line, with no full stop added at its end. An ordered item's number is read at its start. Nesting isn't announced, so a listener hears every item at the same level, in document order. A code block or an image inside a list is silent. It appears only in the page's display. A list item that holds only a code block, an image or a nested list gets no line.
- **A task-list item's checkbox** is silent; whether it is checked or not, the listener hears only the item's own words.
- **Struck-through text** reads as its plain words, with no sign that the source struck it.
- **A blockquote** reads as clean prose, quote marks dropped.
- **A code block** is described in one spoken sentence rather than read aloud: the listener hears what kind of code it is and what it is for, announced with a spoken `Code:` cue ("Code: A Python variable definition."). The source is never read back, and the sentence never claims what the code does. When no description can be made, the listener hears a short honest line ("Code with no description.") rather than silence.
- **An XML-like tagged word** an author wrote about (`<software>`, `<your-api-key>`, `<T>`) reads as the words inside it, brackets dropped, so the listener hears "software" and "your API key". A reader still sees the brackets on the page, because they are the author's own notation for a placeholder or a generic.
- **A table** reads as header-aware prose, never as pipe characters. The audio reads only the body rows, each as its own line with every cell prefixed by its column header ("Feature: Extraction, Status: done."). A row gets a full stop only when it does not already end in one. The header row gets no line of its own.
- **A comparison operator** reads as the word it stands for: `3 < 4` is heard as "three less than four," and a combined form like `<=` as "less than or equal to."
- **An image** is described in the author's own words when there are any, and otherwise in one generated sentence of what it shows. In order of preference the listener hears: the author's alt text, when it is a real sentence; else one generated sentence of what the image shows, announced with an `Image:` cue; else any alt there is; else an honest "Image with no description." rather than silence.

## ✍️ The author's words win, and a description only makes an image visible

Both a code sentence and an image description are generated, so a very code- or image-heavy article carries a budget: only so many descriptions are made. The descriptions go to the blocks that come first in reading order; past the budget a code block falls to its honest short line, and an image falls down its precedence to alt or to the floor. The article still plays start to finish, never failed or silenced for being over budget.

> [!NOTE] A description makes an image visible, it never says what it means
> Meaning comes only from the author, so a real alt sentence always wins where it exists. A generated sentence says what is shown, the decaying fish on the sand, the axes of a chart, and stops there: it makes the image visible without reading anything into it.

> [!NOTE] A code sentence is generated even when the prose just introduced the block
> A tutorial usually names a block in the sentence right before it, so the spoken description often restates what the listener just heard. It is generated anyway: dropping it would take the code off the page for the reader too, which in a tutorial is a real loss, so the block keeps both its window in the audio and its place on the page.

> [!NOTE] A flawed alt is spoken only when a description could not be made
> Alt that is a subscribe prompt, keyword soup, or a bare filename is what sends an image to a generated description in the first place, so it is never spoken on the normal path. It returns only as a last resort, when the description itself could not be produced, because a clumsy line that says an image is there still beats silence that hides it.

> [!NOTE] The audio is clean because of what is extracted, not because of a separate reading mode
> The player renders the same markdown the listener never hears directly. The domain's [recipe](../technical-design/recipes.md) decides what reaches the markdown, and the spoken-form derivation in [article-extraction](../technical-design/article-extraction.md) decides how that markdown is read, so a change to what gets read aloud is a change to one of those two.

## ⏩ What is not built yet

Speaking a quote in a voice distinct from the narration, and adjustable playback speed, are not built.

---

Related: [article-extraction](../technical-design/article-extraction.md) · [listening-experience](listening-experience.md) · [item-contract](../technical-design/item-contract.md)
