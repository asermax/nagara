---
title: "nagara: docs"
aliases:
  - the vault index
tags:
  - index
summary: "The vault: what each folder holds, how files are named, and how to write a note."
---

# nagara: docs

This folder is an Obsidian vault. Open `docs/` as the vault root.

## The folders and what each holds

| Folder | Holds | Index |
|---|---|---|
| `technical-design/` | How the code works: the item lifecycle, article extraction, read-along timing, the TTS service, the item contract, persistence and storage, authentication, deployment and CI, the invariants | [[technical-design/README\|Technical design]] |
| `product-design/` | What nagara *is*: the ながら聞き premise, the listening experience, what gets read aloud, the queue | [[product-design/README\|Product design]] |
| `quest-log/` | The quest log: adventures and quests in one list, told apart by a tag | [[quest-log/README\|The quest log]] |
| `_templates/` | What a new note, quest or adventure is created from | none |
| `_bases/` | The Obsidian bases that generate the lists inside the indexes | none |

Notes live in `technical-design/` and `product-design/`, and which one a note belongs in is a question about its subject, not about who wrote it. Code reading as a short placeholder rather than being read aloud is product design: it is a statement about what a listener experiences. The markdown-it-py token walk that produces that placeholder is technical design. The 100 ms inter-paragraph pause is product design, a number about how listening feels; folding it into the preceding timing window so there is no dead highlight zone is technical design. A note that needs both goes wherever it is *mostly* about and links across.

`quest-log/` holds records rather than notes, and the writing charter below does not apply to it; see its own index for what does. The distinction that matters is that a note explains how something *is*, while a record says what we tried or what we intend to do. When a quest settles something, the outcome moves into a note; the quest stays where it is, as the evidence behind it.

`_templates/` and `_bases/` hold no notes. The underscore is a sorting convention and nothing more: it floats them to the top of the file explorer. Obsidian gives it no meaning and neither folder is hidden.

## Naming, and why it matters

Wikilinks resolve by note name rather than by path, so `[[item-lifecycle]]` works from anywhere and nobody has to track where a file sits. That holds only while file names are unique across the whole vault, which is the constraint behind the naming rule:

A note is named after the aspect it explains, in kebab-case. Not after its folder, not numbered, not dated: a record's date is a frontmatter field (`created`), which is what its index sorts on.

Before adding a note, check the name is not taken. A collision does not error; it silently makes every link to that name ambiguous. Watch in particular for near-collisions between a note and a lab record on a related subject: `read-along-timing` (the technical note) and `read-along-player` (the build quest) and `read-along-player-shape` (the spike that cleared it) all describe adjacent things and must stay three distinct names.

Every folder's index is called `README.md`, so that name is the one deliberate collision here: the payoff is that each index renders as a folder front page when the repository is browsed on the web. Two conventions keep it from costing anything. A link to a *folder's* index names the folder, which disambiguates it: `[[quest-log/README|the quest log]]`. A link to *this* file uses its alias, `[[the vault index]]`, because a bare `[[README]]` written from inside a folder that has its own README is ambiguous at best and a link to itself at worst.

## Frontmatter

Every file carries `title`, `tags` and `summary`, plus `aliases` where a short name is useful. The summary is what shows up in search, in hover previews and in the indexes, so write it as a sentence about the subject rather than about the note.

This file carries the alias `the vault index` for the reason above: it is the only note in the vault that cannot be linked by a path, since its path *is* the ambiguous bare name.

**Tags carry the whole classification.** A note's tag is what puts it in its folder's index; `index` marks an index itself. There is no separate property for any of it, so a query and a reader are looking at the same field.

The indexes are generated from that: each one embeds a base out of `_bases/` that queries the tag. **A note appears in its index by existing**: there is no row to remember to add. The folder table above is the exception that stays by hand, because its rows describe folders and a base has only notes to query.

The corollary is the failure mode worth knowing: **a wrong tag drops a note out of its index silently.** Nothing errors, the note is simply not there.

## How to write a note

**A note explains how one part works.** Mechanism first: the shape of the data, what calls what, in what order, with a diagram when the subject is a flow, a tree or a sequence. A reader should be able to hold that part of the system in their head without opening `api/app` or `tts/app.py` first.

**Reasoning goes in a callout, beside the thing it justifies**, not as the spine of the note:

```markdown
> [!note] Why no headless browser
> A plain fetch handled every HTML fixture tried, including a JS-rendered Substack post: it server-renders its content. The boundary sits further out than assumed.
```

This is a deliberate change from how nagara documented itself before. Every note here started as an ADR or a feature design opening with a requirements table or a decision record, and the effect was that a reader met the argument for the architecture before the architecture itself. The reasoning is still worth keeping (it is what lets a decision be revisited rather than re-argued); it just is not what a reader came for. Per-decision *why* is also the one thing the code already has, densely, at the point of each decision; what code cannot give anyone is the shape of the whole.

Three callout kinds, and they mean different things:

- `> [!note]`: a real choice, and why it went that way.
- `> [!warning]`: a failure mode, what breaks, how it presents, and whether anything catches it. Prefer failures that have actually happened.
- `> [!info]`: an alternative considered and not taken, with the reason it was not.

**A note is not a decision record.** There is no requirements table, no acceptance criteria, no user story, no status ladder. Those describe work being planned; a note describes something that exists.

**A note describes the present.** No "used to", no "previously", no "no longer". An alternative that was rejected is *considered and not chosen, because…*, a standing reason, not a history of the argument.

Create a note from `_templates/note.md`. Point Settings → Templates at `_templates` once, and "Insert template" fills in the title and date. Then **link it from at least one existing note**: a note nothing links to does not get read, generated index or not.

## House style

- **No hard wrapping.** One line per paragraph; let the editor wrap. Diffs then show changed sentences rather than reflowed blocks.
- **Explain the code, do not reprint it.** A note is not a second copy of a declaration. The surface goes in a table of what each member answers, behaviour goes in a diagram or in prose, and a snippet appears only where the code itself is the insight: an exact formula, a guard whose precise form is the point. Two to four lines when it happens. A reader who wants the types opens the file, and what the file cannot give them is why. Written the other way, a note comes out a third fenced code, in a second place where nothing typechecks it and it quietly falls out of date.
- **Mermaid, not ASCII**, for anything with a shape. A state machine, a data model, a request's path through the system and a tree all read faster as a diagram than as a paragraph describing one, and Obsidian and the web view both render mermaid.
- **Headings name their subject.** "Extraction" and "The extraction" give a reader nothing to search for; "the four stages a URL passes through" does. Prefer a heading that could answer a question someone typed into search.
- **Say what a thing is, not what it is not.** Staging a sentence against its own opposite ("it does not reject the paragraph, it drops it") reads as emphasis while carrying no information the plain form lacks. Write the plain form.
- **Prefer commas, colons and full stops to dashes.** A paragraph leaning on dashes is usually one that wants to be two sentences.
- **Write about our implementation.** A comparison with some other tool or library belongs inside a callout that justifies a decision, and nowhere else; a note is not a literature review.
- Close a note with a `---` rule and a `Related:` line linking the notes it actually touches.

## Adding a folder

A folder is four things, and they have to agree:

1. The directory.
2. A `README.md` in it, tagged `index`, carrying that folder's charter and embedding its base.
3. A `.base` in `_bases/` filtering on the folder's tag.
4. A row in the folder table above.

`zenku:init` will do all four and leave anything that already exists alone, or do it by hand from this list: the skills read what is here either way. What breaks is doing three of the four: a folder with no row is invisible to anyone reading this file, and a row with no folder sends people looking for something that is not there.

## Where the reasoning comes from

Before this vault, nagara recorded its decisions as ADRs and DES records and its intent as feature specs and feature designs, all of it grounded in three spikes run against real articles and a real browser. That grounding did not change when the shape did: where a note says a boundary was measured rather than assumed (the HTML-versus-headless line, the highlight-sync latency, the markdown strip's hazards), it is carried over from those spikes, now [[player-ready-item]], [[markdown-paragraph-pipeline]] and [[read-along-player-shape]] in [[quest-log/README|the quest log]]. [[read-along-player]] has no technical note yet for exactly this reason: the player is a solved quest whose real thing is not yet built in `web/`, and a note explains how a part *works*; see `technical-design/README.md`'s "What has no note yet".
