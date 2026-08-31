---
title: "Code blocks dropped before extraction"
tags:
  - quest
summary: "Announced code blocks vanish inside trafilatura.extract and the audio runs an introduction straight into silence; find the condition and stop it."
status: solved
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

## Answer

**Built.** Not `favor_precision`'s pruning heuristics, and the flag is untouched. `prune_html` in `trafilatura/htmlprocessing.py` decides `tails = focus != "precision"` and then deletes every empty element from `CUT_EMPTY_ELEMS` with `keep_tail=tails`. In an XML tree the text *following* an element is that element's tail, so under precision any text sitting behind an empty element leaves with it.

Bisecting the precision-only steps ruled out the heuristics first: neutralising `PRECISION_DISCARD_XPATH`, neutralising `delete_by_link_density` entirely, and forcing its thresholds to the recall side each left the count at 6 `<code>` rather than 9.

### What actually differs between the two pages

Both are Pygments and **both carry the empty opening span on every block**: 3 of 3 on lucumr, 80 of 80 on `t17_realpython.html`. The discriminator is where the listing sits. realpython's is inside a sibling `<code>` element, so the span's tail is empty and cutting it costs nothing; lucumr's is bare text in the `<pre>`, which makes the whole listing that span's tail. "realpython has no empty span" would have been the wrong reading, and it is the one a shallower check produces.

### The fix

`_HOLLOW_ELEMENT_XPATH` in `api/app/service/extract.py`, appended to the `prune_xpath` list the footnote rule already rides on, where `prune_unwanted_nodes` deletes with `keep_tail=True`. One expression, its tag set built at import from `trafilatura.settings.CUT_EMPTY_ELEMS` so the two passes cannot drift, and its emptiness test `not(string(.))` rather than their `not(node())`.

The wider predicate is load-bearing and closes the residual case rather than documenting it. Their pass runs after their own cleaning; ours has to run before it, so a wrapper holding only an icon (`<span><img></span>`) still has a node in it when `prune_xpath` looks and is empty by the time precision cuts it. Matching on an empty string value reaches it without nagara replicating a cleaning list it does not own. Empty rather than blank: `<span> </span>` holds a real space, and deleting it would fuse the words on either side.

### What a listener gets

| | before | after |
|---|---|---|
| units | 13 | 16 |
| spoken words | 551 | 594 |
| code units | 0 | 2 |

All three announcements now run into what they announce. The third block is an English system prompt, so `_is_fenced_prose` reads it aloud in full rather than reducing it to the code placeholder. On `t17_realpython.html` the residual case recovers `Take the Quiz:` twice, a real label that was being cut with its icon span, and closing that `<strong>` again drops the stray bold marker that used to run to the end of the call to action. No fixture loses a spoken word; the three carrying neither shape extract byte-identically.

Two commits: `df3c009` (the rule) and `ec26182` (the residual case), with `what-is-reasoning.html` added as the real artifact and `hollow-element-tails.html` as a probe covering each producer of the shape plus the near misses. `uv run pytest` 233 passed, `ruff check` and `ty check` green in `api/`.

### How far this reaches, and what would make it stop being true

Six HTML fixtures plus the cached article, one machine, on the versions pinned in `api/uv.lock`. It stops being true if trafilatura changes `prune_html`'s tail rule, renames or removes `CUT_EMPTY_ELEMS` (a test fails at nagara's boundary if the import goes), or if extraction is ever run with images on, which would make an image wrapper meaningful and is the one change the text-free predicate is written against.

Not measured: how often the shape occurs across the wider web, and whether the audio for the restored blocks sounds right. The blocks reach `display` and `spoken` correctly; nobody has played the file.


---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[trustworthy-extraction]]
