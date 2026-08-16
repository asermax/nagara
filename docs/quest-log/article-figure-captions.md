---
title: "Article figure captions"
tags:
  - quest
summary: "A figure's caption is the article's own prose about the image, so it is spoken verbatim and the describer is never called; extracting it is per-CMS and undesigned."
status: open
kind: build
adventure: richer-extraction
blocked_by: []
priority: 3-later
created: "2026-08-02"
---

# Article figure captions

## What

Case 1 of the image precedence, and the top of it. When an author wrote a caption, a listener hears the author.

Enqueue a New Yorker photo essay and hear *"Jackie Curtis, circa 1970. Hujar returned again and again to the spiritual life of his sitters…"* rather than a generated sentence about a person in a photograph.

The decision is made. **What is not designed is how to find the caption**, and that is the real work here: every publisher wraps it differently and the credit line has to be excluded.

> [!note] Not to be confused with [[caption-export]]
> Different meaning of the word. That quest is about exporting an item's spoken text as subtitle captions. This is about an image's own figure caption.

## Design

### Why the caption outranks everything

It is the article's own prose about the image, which is higher signal than any generated description could be. So when a caption exists it **is** the spoken form, verbatim, and the describer is not called at all.

That also makes it a cost lever: a captioned image skips a model call entirely, which is part of why every describer figure in the cost model is a ceiling.

The spine is the same one running through the whole image half: meaning comes only from the author, and the describer only makes the image visible.

### The corpus finding that made it load-bearing

The corpus carries authorial figure captions and **they are not `<figcaption>`**. The New Yorker wraps them in `<span class="...caption__text">`:

> "Jackie Curtis, circa 1970. Hujar returned again and again to the spiritual life of his sitters…"
> "'Dead Fish, Fire Island,' 1960-62. The image tells us so much about time and the beauty of unadorned decay."

ACX uses `<figcaption class="image-caption">`. Every CMS differs.

**The credit line is excluded.** "Photograph by Peter Hujar / Courtesy © …" sits in a separate span beside the caption, and only the caption text is taken.

### What this quest has to choose

This is the one part of [[richer-extraction]] whose approach is genuinely undesigned, and it is why this is a quest rather than a paragraph inside another one. Two questions:

**Per-CMS selectors against a heuristic over class names.** A selector per publisher is exact and needs maintaining for every new site. A heuristic over class names containing `caption` is general and will pick up credit lines, share widgets, and whatever else a CMS names that way. Judge it against the cached corpus HTML rather than in the abstract.

**Where it lives.** Inside [[article-image-units]]'s containment pass, which already walks the DOM around each selected image, or as its own step afterwards. The containment pass has the element in hand, which argues for the first; a separate step is easier to test and to extend per publisher, which argues for the second.

Whichever wins, the image-led articles depend on it firing. The New Yorker piece is four contact sheets whose captions are the article's argument.

### Where it sits in the precedence

Above good alt. The full ordering is in [[describe-article-images]]; this quest inserts the top row and nothing else. An image with a caption never reaches the alt filter and never reaches the model.

### How it is verified

Seam 2 for the extractor, against the cached corpus HTML at `prototype_cache/t17_newyorker.html` on `idea/firecrawl-markdown-fidelity`, which is where the `caption__text` finding came from. At minimum: the New Yorker caption is extracted with the credit excluded, the ACX `figcaption` is extracted, and an image with no caption anywhere returns nothing rather than picking up neighbouring prose.

Seam 1 for the precedence: a captioned image reaches `ready` with the caption as its spoken form and **no describer call made at all**, which under cassettes means no cassette interaction.

Per `CLAUDE.md` this is an extraction rule, so it owes a function, a case, a fixture, and a callout in [[article-extraction]].

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[article-image-units]] · [[describe-article-images]] · [[article-extraction]]
