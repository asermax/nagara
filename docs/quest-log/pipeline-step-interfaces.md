---
title: "Pipeline step interfaces"
tags:
  - quest
summary: "Design a step-based pipeline with capability interfaces, positioned by item state."
status: solved
kind: design
adventure:
blocked_by: []
priority: 2-soon
created: "2026-08-17"
---

# Pipeline step interfaces

## What

Make the item pipeline explicit and extensible. Today `advance_queued_item` threads
fetch → extract → enrich → spawn procedurally, and poll drives resolve → store. Introduce
capability interfaces (Fetcher, Extractor, Describer) and a step-based pipeline whose
position is a pure function of the item's own state, so enqueue, retry, and poll become one
`advance(item)` entered at different points. Design only; a follow-on build lands it.

## Design

Two seam layers.

**Capability interfaces** — leaf, config-selectable per invariant 6:

```python
class Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchedPage: ...      # PlainFetcher, FirecrawlFetcher
class Extractor(Protocol):
    def extract(self, page: FetchedPage) -> Extraction: ...  # one impl (invariant 1): TrafilaturaExtractor
class Describer(Protocol):
    async def describe(self, req: DescribeRequest) -> str: ... # GeminiDescriber
```

`FetchedPage`: html, content_type, status, source. `Extraction`: title | None, units. The
Synthesizer (spawn/resolve over Modal) and the two stores are already seams; named here for
completeness.

The plain → firecrawl escalation ("more spoken words wins") is not a Fetcher: it needs both
the fetched HTML and the extracted units to decide, so it sits one level up in SourceStep,
which composes Fetcher + Extractor and owns the comparison. Both interfaces stay pure.

**Pipeline** — one pipeline, position derived from item state, `status` as the phase gate:

```python
@dataclass
class PipelineContext:                    # the item-under-construction, the through-line
    url: str
    voice: str
    title: str | None = None
    html: str | None = None
    units: list[Unit] = field(default_factory=list)
    degradations: list[Degradation] = field(default_factory=list)
    modal_call_id: str | None = None

class PipelineStep(Protocol):
    name: str                             # the error prefix it owns
    def wants(self, item: Item) -> bool   # precondition over item state
    async def run(self, ctx: PipelineContext) -> None

class Pipeline:
    steps: list[PipelineStep]
    async def advance(self, item: Item, db) -> Item   # one entry: enqueue, retry, poll
```

Steps, each gating on the status it advances from and persisting its own effect:

| Step | wants(item) | error prefix | phase · driver |
|---|---|---|---|
| SourceStep | queued, no units | fetch: / extraction: | queued · task |
| ImageStep | queued, units, not enriched_at | enrichment: | queued · task |
| DescribeStep | queued, units, not enriched_at → sets enriched_at | enrichment: | queued · task |
| SynthesizeStep | queued, enriched_at | spawn: | queued · task |
| ResolveStep | generating | tts: | generating · poll |
| StoreStep | generating, remote result in hand | store: | generating · poll |

The runner starts in the item's current status-phase, runs the first step whose `wants`
holds, re-reads the item, continues while the phase is unchanged, and returns when the phase
flips (SynthesizeStep moves queued → generating), a step fails, or nothing wants it. The
queued/generating gate is today's `_write_if_queued` mortality guard, now owned by the runner.
Error-prefix (from `name`), cost metering, and degradation accumulation move into the runner
and off each stage.

Settled: one pipeline positioned by item state; escalation in SourceStep above pure
Fetcher + Extractor; PipelineStep kept as the uniform way to add a step; per-step
persistence; Resolve and Store as two steps.

Out of scope here: the build/migration itself, and whether per-unit (rather than
all-or-nothing) enrichment resume ships — the `wants` preconditions accommodate it, but
DescribeStep stays all-or-nothing until the describer quests want otherwise.

## Answer

Settled in session on 2026-08-17, in conversation with the diagrams that produced it. The
shape is agreed end to end; a follow-on build implements the interfaces and the runner,
replacing the procedural `advance_queued_item` and poll bodies while preserving every
invariant (1 one extraction, 2 one typed unit, 5 no TTS import and the mortal task, 6
config-selected backends). Reopen if the async-gap model changes — streaming-paragraph-audio
would make synthesis multi-result and break the single spawn → resolve handoff this assumes.
</content>
</invoke>
