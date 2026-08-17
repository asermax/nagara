---
title: "Describe article images"
tags:
  - quest
summary: "An image with no caption and no usable alt gets one generated sentence of what it shows, and a describer failure never leaves it silent."
status: solved
kind: build
adventure: richer-extraction
blocked_by: []
priority: 3-later
created: "2026-08-02"
---

# Describe article images

## What

[[article-image-units]] gets images onto the page and speaks their alt text. Most alt is empty, decorative, SEO keyword soup, or a subscribe prompt, so most images still say nothing useful.

This fills case 3 of the precedence: one generated sentence of what the image *shows*, so a listener can picture it.

The describer already exists from [[describe-code-blocks]]. What this adds is the image prompt, the alt-as-context path, and the precedence that decides when the model is called at all.

## Design

### The full precedence

Top to bottom. `Image: ` is prepended for cases 1 through 4; case 5 self-announces and takes no prefix.

| # | Condition | Spoken form |
|---|---|---|
| 1 | caption present | the caption, verbatim |
| 2 | no caption, good alt | the alt, verbatim |
| 3 | no caption, no good alt | **one generated sentence of what the image shows** |
| 4 | generation failed, alt non-empty | any alt, verbatim |
| 5 | generation failed, alt empty | `Image with no description.` |

Case 1 is [[article-figure-captions]]. Cases 2, 4 and 5 arrive with [[article-image-units]]. This quest owns case 3 and the filter that decides between 2 and 3.

### Spine: meaning comes only from the author

The describer makes the image **visible**; it never says what the image *means*. Authorial text is preferred wherever it exists, and the generated description is one sentence of visual content with no second sentence about the image's role in the article.

This was taken consistently across every sub-decision: faithful-to-source and terse over rich and editorialized. It is the same stance [[describe-code-blocks]] takes, with the difference that an image usually *has* authorial text and code never does.

### Good alt: a conservative line

Alt is spoken verbatim only when it is a grammatical sentence, is not the article title (reuse the existing `_is_cruft` title-echo check), and clears a small CMS-boilerplate denylist: `subscribe`, `appears in`, `courtesy`, `photograph by`, `click`, and filename and extension patterns.

Everything else goes to the describer: SEO keyword soup, empty, title-as-alt, subscribe prompts.

> [!note] This inverts the bake-off's "alt as context, never verbatim" on purpose
> The bake-off measured that no clean heuristic separates good alt from bad, and the corpus confirms it: "Image of tank rolling over a world map" (good) and "This article appears in the October 2023 issue. Subscribe to WIRED." (a subscribe prompt) are **both grammatical sentences**. The denylist is the line. It keeps the tank and sends the subscribe prompt to the describer, at the cost of a maintained list a novel boilerplate phrase can slip past.

### The generated sentence

**Specific, never categorical.** A chart's axes are read, a screenshot's UI elements and action are named. Never "a chart" or "a screenshot". Reference quality from the corpus: *"A decaying fish lying on the sand, its skeletal remains exposed."*

**No self-opener.** The sentence begins with the visible thing, and images noun-open naturally: every image output began with "A…" on the first prompt run, unlike code, which needed a second pass. `Image: ` is nagara's announcement.

**The invention guard**, as a sharpened positive instruction with no few-shot: show only, and **do not name people, organizations, brands, places, or regions unless the name appears as written text in the image**. Across the corpus this holds the winner clean, and it collapses the fallback model's editorializing ("AI working collaboratively to orchestrate global changes") to show-only.

The one confirmed invention in the bake-off was geography on the Wired artwork, and no run under this guard reproduced it on either model.

**Alt is passed as context**, labelled as often wrong, empty, or SEO filler, use only what is correct.

> [!note] This closes a gap the bake-off left open
> The bake-off decided alt feeds the prompt and its runner **never actually passed it**. Both of its measured failures had alt that would have prevented them. For the corpus SVG, rasterisation alone solved the case, so alt is belt-and-suspenders there; it earns its place on the images whose alt would have caught a miss.

Structured output and the sanitize tail are inherited unchanged from [[describe-code-blocks]].

### The describer never sees SVG

[[article-image-units]] rasterises on the way in, so the prompt is tuned against rasterised bytes and reads `<text>` labels correctly.

This matters because the winner **rejects raw SVG outright** with a 400, and the fallback accepts it and describes it wrongly, reading a rasterisable diagram as blank boxes. Both are moot in production, and the residual risk, whether the rasteriser renders a given diagram's text legibly, is [[article-image-units]]'s.

### Failure never goes silent

When the describer errors or exhausts its retries, fall back to **any non-empty alt verbatim**, even alt that failed the case-2 filter. Empty alt forces the literal floor.

> [!note] This deliberately inverts the case-2 anti-noise rule on failure
> Bad alt is never spoken in the normal path, because it reaches the describer instead. It is spoken only when the describer is unreachable, because a flawed description ranks above a missing image. The floor is honest: it tells the listener an image is there that could not be described.

So invariant 2's drop-from-both never fires for a **description** failure. It still fires one layer earlier for an **acquisition** failure, which is [[article-image-units]]'s. The two rules do not overlap, and the floor here only ever applies to an image that was fetched and decoded successfully.

A describer failure writes a `{"type": "image", "reason": "describe failed"}` degradation. An acquisition reason can only mean the unit was dropped; `describe failed` can only mean the spoken form fell back.

### No selected image is silenced

Selection is [[article-image-units]]'s and it is settled. Avatars, social buttons, tracking pixels and logos were already removed by containment and the 200px filter before they reach this rule.

The one known false positive per corpus, Real Python's brand logo, gets `Image: the Real Python logo.` and moves on. This precedence has to be answerable for a brand logo, not only for a photograph.

### Cap exhaustion

Past `NAGARA_DESCRIBE_MAX_PER_ITEM`, an image degrades **through this precedence**, so it lands on alt and then on the floor. It is never dropped for being over budget and it never goes silent.

### How it is verified

Seam 1, with the model's response cassetted, asserting on shape rather than on the sentence.

Deterministic assertions worth having: the denylist sends a subscribe prompt to the describer and keeps a real sentence, a title-as-alt is rejected by `_is_cruft`, a recorded describer error falls back to alt that would have failed the case-2 filter, an empty-alt failure produces the exact floor string, and the `Image: ` prefix is nagara's rather than the model's.

Whether one-sentence descriptions land by ear, and whether "Image with no description." reads as honest or flat, is [[richer-extraction-listen-pass]].

## Answer

Built on branch `raid/describe-article-images`, merged to `main` as `6c00293`. Case 3 of the precedence generates `Image: <one sentence>` for an image with no caption and no good alt, reusing the `describe()` core from [[describe-code-blocks]] with the stored WebP fed as an inline part. The good-alt filter (`_is_good_alt`: a grammatical sentence, not the title via `_is_cruft`, clearing a CMS denylist and filename patterns) decides case 2 vs case 3; on describer failure the unit keeps its precedence fallback (any non-empty alt, else the floor), so an image describe never goes silent and never drops.

**Both hard integration points landed.** The describer budget is genuinely shared: `enrich_with_descriptions` now walks the interleaved unit list once into a single document-ordered job list of code units and flagged images, and `NAGARA_DESCRIBE_MAX_PER_ITEM` caps the combined total, so code and images can never each spend a full budget. Over-budget code floors; an over-budget image keeps its precedence fallback. The systemic-fail-raises guard is scoped to code only, so an image-only failure never fails the item. And the cost meter is per-kind: `on_describe(kind)` fires only on a successful call, and lifecycle writes one `describer` CostEntry per call with `detail={"kind": ...}`.

**The cassette is a real recording.** With the key present, `test_describe_images` recorded a genuine Gemini image describe (fixture `bakeoff_realpython.jpg`); the auth header is scrubbed and the YAML carries no key material. It matches on method/host/path/query (not the WebP body) so libwebp or prompt drift can't break replay, and it replays green at record-mode `none`. The recorded answer respected the invention guard, reading the logo's written text rather than naming a brand.

**What would make it stop being true.** A change to google-genai's inline-image request shape (the cassette's request matcher), or a new CMS boilerplate phrase the denylist does not carry (a subscribe-style alt would then be spoken verbatim instead of described). Whether the sentences land by ear is [[richer-extraction-listen-pass]].

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[article-image-units]] · [[describe-code-blocks]] · [[article-figure-captions]] · [[image-extraction-and-alt-text]] · [[richer-extraction-listen-pass]]
