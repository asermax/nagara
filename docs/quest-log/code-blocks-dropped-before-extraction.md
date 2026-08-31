---
title: "Code blocks dropped before extraction"
tags:
  - quest
summary: "Announced code blocks vanish inside trafilatura.extract and the audio runs an introduction straight into silence; find the condition and stop it."
status: open
kind: build
adventure:
blocked_by: []
priority: 1-now
created: "2026-08-30"
---

# Code blocks dropped before extraction

## What

`<pre>` blocks are pruned out of trafilatura's own output tree before any markdown exists, so the prose introducing a block survives and the block does not: the audio runs "GPT-OSS's Harmony response format makes this easy to see:" straight into the next paragraph. Three announced quotations, three silences, on https://lucumr.pocoo.org/2026/8/19/what-is-reasoning/.

Nothing catches it. The item reaches `ready` with 13 units, no `failed`, no degradation recorded, and 551 spoken words clears the 250-word fallback floor by 2x, so the fetch never escalates. This is [[trustworthy-extraction]]'s failure mode: a green pipeline that is not the article.

`favor_precision=True` is implicated but is not the whole story, and this quest does not get to assume it is. With the flag off the same article keeps all three blocks (6 inline `code` spans becomes 9, 0 fence lines becomes 6, 551 words becomes 612), yet `api/tests/fixtures/t17_realpython.html` keeps all 80 of its `<pre>` with the flag on. **Establish what actually differs between those two before changing any configuration**, because turning the flag off globally trades a known silent loss for an unknown one.

`include_formatting` is not a second lever, and trafilatura's external-extractor comparison is not the cause: `fast=True` disables it and changes nothing. Both were ruled out already.

The diff that found this is `spike/xml_diff.py`, with the cached article beside it, on the tag `spike/missing-quotes-and-code-blocks`. The spike's branch was dropped and the tag is what keeps its tree reachable: `git show spike/missing-quotes-and-code-blocks:spike/README.md` names the one command per script, and `git checkout spike/missing-quotes-and-code-blocks` puts the whole tree back.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[trustworthy-extraction]]
