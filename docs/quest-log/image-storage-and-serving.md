---
title: "Image storage and serving"
tags:
  - quest
summary: "An ImageStorage beside AudioStorage on a shared base, keyed by a content hash of WebP bytes, served from an auth-guarded route that mints at read time."
status: open
kind: build
adventure: richer-extraction
blocked_by:
  - async-api-migration
priority: 3-later
created: "2026-08-02"
---

# Image storage and serving

## What

The seam that lets nagara hold an article's images on its own storage rather than hotlinking them.

Hand it image bytes and get back a content hash. Ask for that hash under an item and get the image served, locally from a file and in production from the bucket, behind the same key as audio.

Verifiable on its own with a committed fixture image, before anything knows how to find an image on a page. [[article-image-units]] is the quest that fills it.

## Design

### Shape: a shared base class, two interfaces

A base class holds the common storage code, the local-directory and bucket-client machinery. `AudioStorage` and `ImageStorage` inherit it as two specialised interfaces.

Images differ from audio on every axis: many per item rather than one, fetched from an origin rather than handed in as bytes, keyed for cross-article dedup rather than by item id, and served by a URL embedded in persisted markdown. So they earn their own contract. Factoring the put-object and serve backend into the base avoids copy-pasting the bucket client without collapsing two different semantics into one interface.

Invariant 6 holds: one factory, one `s3_configured` switch, no branch.

### Keying: a content hash of the stored bytes

Not the item id, and not the origin URL. Hashing what gets stored dedupes for free across items, across re-enqueues of the same article, and across a repeat of the same image within one article, which happens whenever `og:image` is echoed in the body.

It is also the pattern [[audio-caching-by-url-and-voice]] will likely reuse, so getting it right here de-risks that.

### Acquisition: decode-validate, then the describer's four formats

A ~10 second per-image fetch timeout. Stream and abort if the body exceeds ~10 MB, which bounds memory during decode.

**Validate the real format by decoding with Pillow, never by trusting the `Content-Type` header**, which is wrong or missing on most image CDNs. Accept JPEG, PNG, GIF and WebP, which is the describer's set. Follow redirects. `data:` URIs decode in place under the same rules.

The decode is dual-purpose: [[article-image-units]]'s dimension filter needs the decoded dimensions anyway.

### Re-encode to WebP before storing

So the content hash is over the WebP bytes. This shrinks storage and dedupes across source-format variants of the same image, since a CDN serving JPEG here and WebP there collapses to one stored object. WebP is describable by the model and displayable by every modern browser.

The cost is a lossy transcode and a Pillow encode step, and Pillow is already the decode dependency. Animated GIFs collapse to a static first frame; the describer uses only the first frame anyway, so the audio side is unaffected and the display loses motion for the rare animated figure.

### Serving: a dedicated route, minted at read time

`GET /items/{id}/images/{hash}`, mirroring `GET /items/{id}/audio` exactly: `FileResponse` locally, `RedirectResponse` to a fresh presigned URL in the bucket.

**Persisted links never expire.** A presigned URL written into the row would be dead inside `s3_url_ttl`, which is 3600 seconds, and the unit list is persisted indefinitely. The path is reconstructed at read time from the item id and the hash.

The route requires the key, inheriting audio's auth story, so invariant 4 holds uniformly. Per `CLAUDE.md` a new route owes an endpoint module, a pydantic schema, and a section in [[item-contract]].

### Half-configured inherits the audio rule

The same factory on the same `s3_configured` switch, so three of four S3 fields counts as not configured and the image store falls back to local storage exactly as audio does. Visibly, rather than crashing obscurely. No second rule and no image-specific flag.

### How it is verified

`test_storage.py`'s existing seam, which already drives the local-against-bucket choice through configuration, plus seam 1 for the route.

The round trip is the assertion worth making hardest, because it has never been run: a real corpus image through fetch, decode, re-encode, hash, store and serve. Then the same image a second time, which must hit the stored object rather than re-fetching.

Cassettes do not cover image bytes at scale. A fetched image is base64 in the YAML, large and not diffable, and `tests/fixtures/` is text-only today. Use a committed fixture image and treat the image-fetch GET as a thin client with at most one representative cassette.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[persistence-and-storage]] · [[item-contract]] · [[article-image-units]] · [[audio-caching-by-url-and-voice]]
