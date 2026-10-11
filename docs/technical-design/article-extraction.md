---
title: "Article extraction"
summary: "How the item Workflow fetches an article and turns the recipe's markdown units into the item's typed units: a spoken form derived from each unit's display, a drop for a unit with nothing to say, and the acquisition of the article's declared images through the Images binding."
created: "2026-07-29"
---

# Article extraction

## 🔭 Overview

The item Workflow fetches an article's HTML, runs the domain's [recipe](recipes.md) on it, and turns what comes back into the list of typed units that every later step reads. The recipe returns a title and markdown units: paragraphs, code blocks and declared images. The item Workflow derives each text unit's spoken form from its display markdown, drops a unit whose spoken form has nothing to say, and acquires each declared image. The result is one list in which every unit carries its `display`, its `type` and its `spoken` form (see [item-contract](item-contract.md)); what a described unit says comes from [image-and-code-describer](image-and-code-describer.md).

## 🌐 Fetching the page

The item Workflow's fetch step scrapes the page through Firecrawl with its own fetch-based client. Its raw HTML goes to the recipe step unsegmented. The domain of the final URL, after redirects, picks the recipe. A scrape that cannot reach Firecrawl, or returns no HTML, fails the step; once the step has used its 3 attempts the item fails, with `current_step` naming fetch (see [item-lifecycle](item-lifecycle.md)). The fetch step writes what each scrape bills, from Firecrawl's `creditsUsed`, as a ledger row (see [persistence-and-storage](persistence-and-storage.md)), so a failed item still records the credit it spent.

> [!NOTE] What firecrawl is called with, and why rawHtml
> The scrape asks for `rawHtml` and `markdown` at `proxy: "auto"`. The fetch step asks for `rawHtml` rather than firecrawl's cleaned HTML because the cleaning throws away images (9 against 5 on one corpus article), and the recipe declares the article's images from the page's own markup. `markdown` costs no extra credit, so the fetch step requests it as evidence; nothing reads it. `proxy: "auto"` bills 1 credit when a basic proxy suffices and 5 on a stealth escalation.

> [!WARNING] firecrawl's output is non-deterministic
> The same URL scraped minutes apart returned a 5x spread in size, and `rawHtml` is post-JavaScript, so it can carry hydrated page chrome a plain fetch never had. The recipe's container and ignores are what keep that chrome out of the units. The spread affects re-recording a test cassette, never a replay, which returns recorded bytes verbatim.

## 📩 How the recipe's units become typed units

```mermaid
flowchart TD
    start(["The recipe returns<br/>a title and<br/>display units"]) --> loop
    subgraph loop ["Recipe step: each recipe<br/>unit, in document order"]
        direction TB
        kind{"Image unit?"}
        kind -->|No| spoken["1 Derive the spoken<br/>form from the display"]
        spoken --> test{"2 Drop rule<br/>matches?"}
        test -->|Yes| drop["3 Drop: no typed unit"]
        test -->|No| keep["4 Keep as a typed<br/>paragraph or code unit"]
        kind -->|Yes| stash["5 Hold it after the<br/>last kept text unit"]
    end
    subgraph images ["Images step"]
        direction TB
        acquire["6 Acquire held images,<br/>interleave with kept units"]
        acquire --> any{"7 Any unit survives?"}
        any -->|Yes| write["8 Write the units<br/>into the item row"]
    end
    loop --> acquire
    any -. no .-> fail(["Fail the item:<br/>no surviving units"])
    write --> next(["Describe, synthesis,<br/>store: survivors only"])
```

Steps 1 to 5 run at the end of the item Workflow's recipe step, on the units the recipe returns. Steps 1 and 2 are in a required order, because the drop rule reads the spoken form. The loop must also run in document order, because step 5 anchors an image to the last text unit kept so far. When that unit is dropped, the image anchors to the kept unit before it. An image that comes before every text unit goes first in the list. The recipe step writes the kept text units into the item row and hands the held images to the images step as its step result, each with its src, its alt and the kept unit it follows, so the row holds only finished units. Steps 6 to 8 run in the images step. It acquires the held images, places each after its unit and drops any that will not acquire (see below). It fails the item when no unit survives. It writes the full list and the degradations into the item row, and the later steps read them from there. The recipe step writes the title into the row together with its units. A recipe the agents authored or revised is written as its next version by the item Workflow itself (see [recipes](recipes.md)).

From step 8 on, describe, synthesis and store work on the survivors only and never drop a unit, so the length guard at store compares one list against its own timeline (invariant 2).

> [!NOTE] Why the display list is persisted rather than re-extracted
> The display list is written onto the item row as the steps produce it and joined onto the timing at store (see [item-contract](item-contract.md)) rather than re-fetched and re-extracted when synthesis completes. Re-extracting risks a different result across the async gap: the same URL a minute later is not guaranteed to produce the same page. The API shows the units only once the item is `ready`.

The unit list's shape, including `ImageUnit`, is a type in common/ that both Workers build against (see [common-package](common-package.md)).

## 🗣️ Deriving the spoken form

The spoken form is derived from the unit's display markdown by walking its CommonMark token tree, so the display and spoken forms come from one extraction (invariant 1). A fenced code block becomes the fixed placeholder `"Code sample."`. A table is spoken as its body rows only, each row as its own line of header-aware prose (`"Feature: Extraction, Status: done."`) and never as pipe characters. The header row gets no line of its own. A row gets a full stop only when it does not already end in `.`, `!` or `?`. A cell goes through the same inline walk as a paragraph, so a code span keeps its text, and then through the sanitize tail, described below. A heading and a quote are read as their words, without their markers. Every block inside a unit becomes its own line, so a unit carrying several paragraphs or list items never runs the last word of one into the first word of the next. A list item gets no full stop. An ordered item keeps its `1.` at the start of its line, and the spoken form does not announce nesting depth. A code block or an image nested inside a list unit is silent in the spoken form. It stays inside the list's own display and is never described or acquired on its own (see [markdown-units](markdown-units.md)). A list item that holds only a code block, an image or a nested list gets no line. The derivation strips a task-list checkbox and reads struck-through text as its words, with no sign of the strike. Emphasis markers and link destinations are dropped throughout.

A shared sanitize tail then turns any leftover emphasis or code marker that touches text into a space, so the newlines between a unit's lines survive the pass. It drops the space a marker left before punctuation and collapses whitespace. It reduces an opening or closing tag around a word to the word inside (`<software>` to "software", `</div>` to "div"). A lone `<` or `>` is not a tag, so this step leaves it for the operator rule that follows. A last pass turns a comparison-operator sequence into the word it stands for, longest match first: `<=` "less than or equal to", `>=` "greater than or equal to", `->` "to", `=>` "to", `<-` "from", `<<` "much less than", `>>` "much greater than", `<3` "heart", then the bare `<` "less than" and `>` "greater than". `<3` becomes "heart" only when no digit follows, so `<30` reads "less than 30". The pass puts a space on each side of every word it inserts, so `a<b` reads "a less than b". The describer's model output runs through the same tail (see [image-and-code-describer](image-and-code-describer.md)), since a JSON schema cannot forbid a marker inside its string value.

The `"Code sample."` placeholder is the **interim** spoken form of a code block. During the describe step the describer overwrites a code unit's spoken form with `Code: <one sentence>` and a describable image's with `Image: <one sentence>`; a code block keeps the floor `"Code with no description."` only when the describer fails or the per-item budget is spent.

> [!NOTE] The words inside a surviving tag are the article's own
> An author writing about software writes `<software>`, `<your-api-key>` or `<T>` as text, and a tag still present in a unit's markdown is prose the author escaped. Dropping it silently loses a word the article meant to say, and a whitelist of real HTML element names would be actively wrong here, since an author writing about `<div>` intends the listener to hear "div".

## 🗑️ Dropping a unit with nothing to say

```mermaid
flowchart TD
    A["Text unit from the recipe,<br/>with its spoken form"] --> C{"Spoken form has a<br/>letter or digit?"}
    C -->|No| D((Drop))
    C -->|Yes| K((Keep))
```

The rule runs on every paragraph and code unit the recipe returns and reads only the spoken form: a letter inside a link URL or a code block's language tag never keeps a unit. "Letter or digit" follows Unicode, so non-Latin text is kept. An empty spoken form fails the same test. A dropped unit never becomes a typed unit, so its display, its spoken form and its timing window leave together (invariant 2), and it leaves no trace: no degradation, no log.

What the rule catches is a section-break ornament (`❦`, `* * *`, `§`) or bare punctuation that a recipe emitted as its own paragraph. A code unit always passes, because its spoken form is the `"Code sample."` placeholder.

> [!NOTE] Why a drop leaves no trace
> The rule drops only units whose spoken form carries no letter or digit, so what disappears is never a word the author wrote. A degradation records content the item lost, and an ornament carries no content.

> [!WARNING] A unit with nothing to pronounce crashes synthesis
> The synthesizer produces no audio for a paragraph made only of a symbol, and the TTS service fails the whole call on it. A sockpuppet.org recipe that kept its `❦` section breaks as paragraphs failed its items at synthesis while every extraction step reported success. The drop is what keeps such a unit from reaching synthesis.

> [!TIP] Rejected: echoed-title and navigation-label matching on recipe units
> The recipe already names the title element and carries the ignore list the author agent wrote, so an echoed title or a "Contents" label is the recipe's to exclude. Matching them again after the recipe step would add a heuristic that repeats a decision the recipe already makes.

## 🖼️ Article images: acquisition and spoken form

The recipe declares which images belong to the article: each image unit carries its `src` and `alt`, and the images step acquires exactly the images the recipe declares, with no selection of its own. Each acquired image gets a spoken form and goes after the text unit it followed in the page. Each image is an `ImageUnit` with its own spoken form and therefore its own timing window.

### ⬇️ Acquisition: download, validate, re-encode, store

A declared image is downloaded under a per-host semaphore (default 2) beneath a global one (default 10), with a 10-second timeout and a 10 MB streamed size cap. The per-host bound is the one that matters: one article's many same-host images must never open that many connections to a server nagara has no relationship with. A Workers instance holds 6 outbound connections at a time, so at most 6 downloads run at once whatever the global bound.

Validation runs on the **decoded bytes**, never on HTTP or HTML metadata. The bytes are sniffed for an `<svg` root. A raster image goes through Cloudflare's Images binding, which decodes it outside the Worker, and is **kept when `min(width, height) >= 200`**, measured on the decoded file. What survives is re-encoded to WebP through the same binding. Each kept image is stored once per content hash, taken over the stored bytes, under the images prefix of the R2 bucket, with its content type on the object, and the hash becomes the unit's image reference, so no origin URL leaks into persisted markdown. common/'s image key function builds the object's key from the hash (see [common-package](common-package.md), and [persistence-and-storage](persistence-and-storage.md) for the bucket layout).

> [!NOTE] Why validate by decoding, not by trusting the attributes or the Content-Type
> Most of the corpus omits `width`/`height` entirely (all four New Yorker contact sheets carry neither), and a Content-Type header can lie, so the only trustworthy size and format come from decoding the file itself. The 200 px floor sits in a gap in the corpus: avatars and tracking pixels cluster around 40 px and every legitimate figure is 305 px or larger. Two square brand logos survive it, accepted rather than chased, because a square-ratio rule has no legitimate square image in the corpus to test against and a false positive costs only one cheap describe call.

An SVG stays an SVG. Its scripts are stripped before it is stored, and it is stored under the content hash of the stripped markup, with the SVG content type on the object. It has no pixel size to measure, so the 200 px floor does not apply to it. It is describable from its markup (see [image-and-code-describer](image-and-code-describer.md)) and is served like any other image; a client shows it only through an `<img>` element, where its scripts would not run (see [item-contract](item-contract.md)).

> [!TIP] Rejected: an image library inside the Worker
> The Images binding rejects every SVG, so rasterising one would take a WebAssembly rasteriser in the Worker: about 1.5 MiB gzipped added to the bundle, and every text element in the SVG disappears unless a font is bundled with it. Decoding a raster above about 10 MP inside the Worker exceeds its 128 MB of memory and ends the invocation where no code can catch it. The binding decodes rasters outside the Worker's memory, and a browser renders an SVG natively, so keeping the SVG needs no rasteriser at all.

### 💬 An image's spoken form

An acquired image speaks its alt verbatim as `Image: <alt>`, or the floor `"Image with no description."` when the alt is empty. The good-alt filter decides whether the describer replaces that form with a generated sentence (see the precedence in [image-and-code-describer](image-and-code-describer.md)). One of its checks is the cruft test: an alt that repeats the article title, or carries no letter or digit, is not a good alt.

### ❌ An image that will not acquire is dropped from both lists

An image that 404s, times out, exceeds the size cap, will not decode, or fails to process through the Images binding is dropped from `display` and `spoken` alike (invariant 2), and the drop is recorded as a `degradation`: a typed object `{"type": "image", "url": <origin>, "reason": <short>}` that never rides on the wire. This is acquisition failure only, kept distinct from a **describe** failure, which never goes silent (see [image-and-code-describer](image-and-code-describer.md)). The two divide by layer: an image that never arrived has no unit to speak for, so it drops; an image that arrived but could not be described keeps a spoken fallback.

> [!NOTE] Why a degradation column, when the item is still `ready`
> `error` stays failed-only, and that rule is worth keeping. A `ready` item that silently dropped six of twelve images exposes nothing to the client and a full record to the operator: technically `ready` and quietly worse. The degradation list is what makes that visible without failing the item. Its scope is runtime degradations only.

## ⏩ What is not built yet

- **Prose-boilerplate stripping.** Footer donation asides and sponsor mentions arrive as full sentences and reach the audio unless the recipe ignores them. The item Workflow does not filter them, because a generic filter risks trimming real content.
- **Quote voice switching.** A listener hears a quote in the one narrator voice, and nobody has yet validated the blockquote audio round-trip end to end.

---

Related: [recipes](recipes.md) · [markdown-units](markdown-units.md) · [image-and-code-describer](image-and-code-describer.md) · [item-lifecycle](item-lifecycle.md) · [read-along-timing](read-along-timing.md) · [item-contract](item-contract.md) · [tts-service](tts-service.md) · [persistence-and-storage](persistence-and-storage.md) · [common-package](common-package.md) · [invariants](invariants.md) · [what-gets-read-aloud](../product-design/what-gets-read-aloud.md)
