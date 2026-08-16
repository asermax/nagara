---
title: "Article image units"
tags:
  - quest
summary: "DOM containment finds the article's own figures, they download onto nagara's storage, and each becomes an image unit with its own timing window."
status: solved
kind: build
adventure: richer-extraction
blocked_by: []
priority: 3-later
created: "2026-08-02"
---

# Article image units

## What

Enqueue a New Yorker piece about photographs and get its four contact sheets as image units, each with a working image URL and a spoken form. Today all four are dropped and the author's avatar is kept.

An image-only unit strips to empty text and vanishes from both lists, so a listener never learns it existed and a reader never sees it. This is what gives it a spoken form, which is what lets it survive as a unit at all.

Descriptions come later. This quest speaks the alt text, or the honest floor when there is none, and [[describe-article-images]] upgrades that. The point of splitting them is that images work end to end before a model is involved.

## Design

### The source: DOM containment

Three recovery mechanisms were tried and failed before this one. `bare_extraction().body` returns a rebuilt tree with images already excluded, so there is nothing to mine. Rewriting every `<picture>` to its inner `<img>` changed trafilatura's output by **zero bytes**, because it prunes the whole figure subtree as non-article rather than failing to see an element. Positional anchoring over firecrawl markdown worked on one corpus entry in three.

The fourth works, and it runs on the article's own HTML, so it behaves identically on the plain-fetch and fallback paths.

Trafilatura already found the prose, so its paragraphs are probes back into the original tree. For each of the longest units, find the **deepest** element whose text content holds the probe. Then score every ancestor of every anchor by how many anchors it contains, and take the **deepest element holding at least 80% of them**.

Scoring containers this way, rather than taking a strict lowest common ancestor, is what makes it survive one bad match. A single stray anchor in a footer would otherwise collapse the answer to `<body>`.

**Plus `og:image`**, which recovers the lede. Containment systematically misses it, because the hero sits above the article body element on both Condé Nast sites. The New Yorker's `og:image` is exactly the contact sheet the container excluded.

> [!warning] Two implementation facts that each cost a rewrite in the prototype
> **lxml element proxies are recreated per access, so `id()` is not a stable identity.** A membership set built from `id()` silently produces nonsense. Use paths from `getroottree().getpath()`.
>
> **The probe must skip `<script>`.** Both Condé Nast sites carry a JSON-LD copy of the article body, so an unfiltered probe anchors inside it and drags the container to the document root.

### What it measures

| Article | `<img>` on page | Selected | Got | False positives |
|---|---:|---:|---|---|
| newyorker | 9 | 5 | all four contact sheets plus the lede | **0**, two logos and the headshot excluded |
| wired | 19 | 5 | the four commissioned artworks plus the lede | **0**, all twelve related-article thumbnails excluded |
| acx | 13 | 10 | six figures plus four embedded-tweet media | 0 |
| realpython | 27 | 3 | lede plus the Python-logo figure | 1, a brand logo |
| simonwillison | 1 | 1 | the mermaid diagram | 0 |

The class this was written about is gone. Wired's "Stop Saying Kids Can't Read" and Real Python's eleven author avatars are all outside the container.

**Firecrawl's markdown is not the source**, tested directly: 13 images on Wired, twelve of them related-article headlines and **zero of the artwork**, with `src` resolving to the literal string `undefined` because they lazy-load and never hydrate. On ACX it carries 454, of which 442 are commenter avatars. Containment beats it on every entry and works where firecrawl never ran.

**When no container is found, fall back to `og:image` alone**, then apply the same filter. It is the publisher's own declaration rather than a guess, and it was a real figure on all five corpus articles that have one. Anchoring succeeded on 6 of 6 after the `<script>` and depth fixes, so **this path is untested in practice**. Its worst case is thin rather than wrong.

### Selection finishes after download

Containment picks candidates; a filter on the decoded file removes what is left. The filter runs on the real file rather than on HTML attributes, which matters because most of the corpus omits them: all four New Yorker contact sheets carry neither `width` nor `height`.

**Keep an image when `min(width, height) >= 200`.** The corpus separates on a canyon:

```
   40 px  acx tweet avatars       drop
  200 px  ──── threshold ────────────
  305 px  acx og:image            keep
  459 px  realpython figure       keep
  671 px  wired lede              keep
 1334 px  newyorker contact sheet keep
```

Two survivors are accepted rather than chased. Real Python's brand logo at 1920x1920 is only caught by a square-ratio rule, and no legitimate square image exists in the corpus to test that rule against, since an Instagram-style crop is exactly square. A false positive costs one cheap describe call and a sentence of audio, which is the cheaper error.

### SVG rasterises on the way in

An SVG cannot be decoded to WebP by Pillow, so it is rasterised to PNG at a fixed render resolution before entering [[image-storage-and-serving]]'s pipeline, after which it is describable and displayable like any raster image.

**The 200px filter does not apply to it.** An SVG has no intrinsic pixel size, and after rasterisation the resolution is chosen rather than measured. The figure already passed containment selection as a real image.

Diagrams are disproportionately SVG in technical articles, which is nagara's core corpus, and the corpus's mermaid diagram is the concrete case.

> [!warning] Verify the rasteriser deploys on Railway before building the path
> cairosvg needs cairo and resvg needs a binary, and neither may install cleanly on the Railway image. **Check this first.** If it does not deploy, the decision degrades to storing the SVG as-is for display and describing from alt text only, or dropping SVG units, rather than reopening the question.
>
> The render resolution is unnamed. 768px width read the corpus diagram's `<text>` labels correctly in the prototype, and the number wants eyes on a real diagram rather than a guess.

If rasterisation fails, the spoken form degrades to alt text, or to silence if there is none.

### Fetch bounds, and courtesy to hosts nagara has no relationship with

A dict of per-host semaphores at `NAGARA_IMAGE_FETCH_PER_HOST` (default 2), under a global `NAGARA_IMAGE_FETCH_CONCURRENCY` (default 10). Both settings, per invariant 6.

The per-host bound is the one with teeth. One article's 27 same-host images must never open 27 connections to that server.

### Acquisition failure drops the unit from both lists

An image that 404s, times out, exceeds the ceiling, or will not decode is **dropped from display and spoken alike**, per invariant 2. The reader loses the image and the audio never mentions it: a silent gap.

This reuses the existing drop path rather than inventing a degraded-unit state. An image-only unit with no spoken form is already dropped today, and a failed image is the same case: no describable content, so no spoken form, so dropped. No origin URL leaks into persisted markdown, which keeps the self-hosting story clean.

> [!important] This is acquisition failure only, and it does not overlap with description failure
> [[describe-article-images]] owns what happens to an image that **arrived** and could not be described, and that path never goes silent. An image that never arrives has no unit to speak for. The two rules divide by layer, and both must be read before either is built.

### The `degradations` column arrives here

An image drop is the first thing in the pipeline that can degrade an item without failing it, so the column lands with this quest, plus its migration.

A JSON list of typed objects, **never on the wire**, accumulated in memory during the fan-out and flushed with the same write that flushes units, so there is no concurrent read-modify-write on the row:

```json
{"type": "image", "url": "<origin url>", "reason": "404"}
```

`type` takes its values from [[typed-unit-contract]]'s discriminator, so in practice only `image` and `code` ever appear: a paragraph cannot enrich, so it cannot degrade. `reason` is short (`404`, `timeout`, `undecodable`, `svg rasterise failed`, and later `describe failed`), and the drop-against-fallback outcome rides on it. `url` is the origin, the locator worth re-fetching, since a dropped unit has no surviving index.

This exists because `error` stays failed-only and that rule is worth keeping. A `ready` item that dropped six of twelve images exposes nothing to the client and a full record to the operator. That is the [[trustworthy-extraction]] family from a new direction: technically `ready` and quietly worse.

Scope is runtime degradations only. The table-cell whitespace loss and the fenced-prose re-classification are data-quality defects rather than runtime failure decisions.

### The spoken form, for now

Alt text verbatim when present, and the literal `Image with no description.` when not, both behind an `Image: ` prefix for the alt case. [[describe-article-images]] inserts the generated sentence and [[article-figure-captions]] inserts the caption above it.

Every image unit that reaches the list carries a spoken form, so it always has a timing window and no display-only unit is needed.

### How it is verified

Seam 2 for containment, driven by the cached corpus HTML at `prototype_cache/t17_*.html` on `idea/firecrawl-markdown-fidelity`, which is what makes the table above re-runnable offline. Seam 1 for the end-to-end path: enqueue a fixture article, get image units with working URLs and degradation records for the ones that failed.

`prototype_image_features.py` and `prototype_image_download_filter.py` on that branch carry the working algorithm.

## Answer

Built. `api/app/service/images.py` carries the containment algorithm, the async image acquisition, SVG rasterisation, and document-order interleaving. The lifecycle calls `enrich_with_images` between segmentation and spawn.

The extraction path (`extract_article`, `extract_with_fallback`) now returns the HTML alongside title and units, so the image selector probes into the same tree the extraction read. Migration `a4e7f2b91c56` adds the `degradations` column. `NAGARA_IMAGE_FETCH_PER_HOST` and `NAGARA_IMAGE_FETCH_CONCURRENCY` are live settings.

15 new tests cover containment (synthetic and corpus fixtures), og:image, dedup, document-order positioning, interleaving, size filter, SVG detection, and SVG rasterisation.

**What stops being true.** The cairosvg dependency needs cairo as a system library. It installs locally but has not been verified on Railway's image. If Railway does not carry cairo, SVG images degrade to dropped units with a `"svg rasterise failed"` degradation — the fallback path is built and tested. The 768px rasterisation width was chosen from the prototype's mermaid diagram; a real diagram on production content may want a different number.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[image-extraction-and-alt-text]] · [[image-storage-and-serving]] · [[describe-article-images]] · [[article-figure-captions]] · [[typed-unit-contract]] · [[trustworthy-extraction]]
