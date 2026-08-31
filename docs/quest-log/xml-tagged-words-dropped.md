---
title: "XML-tagged words dropped"
tags:
  - quest
summary: "Audio silently drops words wrapped in XML-like tags; strip or escape them before they reach the TTS."
status: solved
kind: build
adventure:
blocked_by: []
priority: 1-now
created: "2026-08-30"
---

# XML-tagged words dropped

## What

Audio silently drops words wrapped in XML-like tags (e.g. `<software>`). The TTS engine appears to strip tagged tokens instead of reading the word content. Needs investigation — either strip tags before sending to TTS, or escape them properly.

## Answer

Built. The cause was not the TTS engine: `_to_spoken`'s token walk handled `text`, `code_inline`, softbreak/hardbreak and `_open`/`_close`, and CommonMark parses `<software>` as an `html_inline` token, which fell through every branch and was discarded before synthesis. Kokoro reads `<software>` as "software" whether or not the brackets are stripped, so nothing downstream was ever losing the word.

A worse half sat behind the reported one: a unit that is *only* a tag parses as an html **block**, so the inline walk emitted nothing for it, and the empty-spoken rule then dropped the whole paragraph from `display` as well. An entire paragraph vanished from page and audio with nothing failed and nothing logged.

One regex (`_TAG_SHAPE`, drawn on markdown-it's own boundary) now serves both forms, per invariant 1. `_normalize_display` backslash-escapes the tag's `<` inside its existing mask, so a client renders the author's word and code spans and fenced blocks keep their raw brackets; `sanitize_spoken` reduces the tag to the words inside it, accepting the escaped form too, since `_table_to_spoken` reads a cell off the raw inline source. Restoring the word exposed a latent fusion the drop had been hiding (`**bold**<software>` spoke "boldsoftware"), so `<` joined the fused-character set in `_fuses` and in the emphasis pass.

Reach: 15 cases in `api/tests/test_extract.py` plus the `tagged-words.md` fixture, a pre-registered synthetic probe because no corpus article reaches this case at all (trafilatura strips every real element, so a tag only survives when an author escaped one, and none of the four fixtures does). Verified audibly by running Kokoro 0.9.4 on CPU locally and reading the phonemes: "We ship ... to users" became "We ship software to users", and `<your-api-key>` reads "your A-P-I key". The display claim is checked against markdown-it under both `html: true` and `html: false`, not against a player, because `web/` does not exist yet.

Left alone deliberately: a bare comparison operator (`3 < 4`) is not a tag, so both forms keep it exactly as the author wrote it, and Kokoro voices neither character. That silence is recorded in [[what-gets-read-aloud]] and [[article-extraction]] as not built yet; speaking an operator is a reading rule of its own.

What would make it stop being true: trafilatura beginning to pass real markup through into its markdown output, which would make "a surviving tag is the author's prose" false and turn the rule into a source of spoken junk. A client that renders markdown with its own escaping rules could also disagree with the backslash.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[what-gets-read-aloud]]
