import base64

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ...config import settings
from ...helpers import now_iso
from ...models.item import ItemStatus
from ...schemas.tts import SynthesisResult
from ..cost import record_describer_cost, record_firecrawl_cost, record_tts_cost
from ..describe import enrich_with_descriptions
from ..fallback import extract_with_fallback
from ..images import enrich_with_images
from ..storage import audio_ext, audio_storage
from ..tts import Synthesizer
from .context import PipelineContext


class SourceStep:
    """Fetch and segment the URL into typed units. Composes the fetchers and the one extractor
    through ``extract_with_fallback``: the plain fetch first, firecrawl as a fallback fetch, and
    more-spoken-words wins — so the escalation policy sits above the pure Fetcher/Extractor
    seams. A billed firecrawl scrape is metered even when extraction then fails, so the credit
    is recorded on its own commit that an abandoned item write cannot swallow."""

    name = "source"
    phase = ItemStatus.QUEUED

    def wants(self, ctx: PipelineContext) -> bool:
        return not ctx.enriched_at and ctx.html is None

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        def capture(usage) -> None:
            ctx.firecrawl_usage = usage

        try:
            title, units, html = await extract_with_fallback(
                ctx.url, settings.firecrawl_api_key, capture
            )
        finally:
            if ctx.firecrawl_usage is not None:
                await record_firecrawl_cost(db, ctx.item_id, ctx.firecrawl_usage)
                await db.commit()

        ctx.title = title
        ctx.units = list(units)
        ctx.html = html
        ctx.write = {"title": title, "units": [unit.model_dump() for unit in units]}


class ImageStep:
    """Select, acquire, and interleave the article's own images into the unit list. Runs only
    after the source fetch, so it has the HTML to probe; an acquisition failure drops the unit
    from both lists and records a degradation rather than failing the item."""

    name = "enrichment"
    phase = ItemStatus.QUEUED

    def wants(self, ctx: PipelineContext) -> bool:
        return not ctx.enriched_at and ctx.html is not None

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        html = ctx.html
        if html is None:  # guaranteed by wants; narrows the type for the call below
            return
        units, degradations, requests = await enrich_with_images(
            html, ctx.url, ctx.title, ctx.units, ctx.item_id
        )
        ctx.units = list(units)
        ctx.image_requests = requests
        ctx.degradations += degradations
        ctx.write = {"units": [unit.model_dump() for unit in units]}


class DescribeStep:
    """Describe code blocks and case-3 images against one shared budget, then mark enrichment
    finished. The describer calls are metered on their own commit; ``enriched_at`` is the flag a
    retry reads to re-spawn synthesis without re-fetching, so it is written here with the final
    unit list once every unit has resolved its spoken form."""

    name = "enrichment"
    phase = ItemStatus.QUEUED

    def wants(self, ctx: PipelineContext) -> bool:
        return not ctx.enriched_at

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        def count(kind: str) -> None:
            ctx.describe_kinds.append(kind)

        units, degradations = await enrich_with_descriptions(
            ctx.units,
            ctx.title,
            image_requests=ctx.image_requests,
            api_key=settings.gemini_api_key,
            on_describe=count,
        )
        ctx.units = list(units)
        ctx.degradations += degradations

        if ctx.describe_kinds:
            for kind in ctx.describe_kinds:
                await record_describer_cost(db, ctx.item_id, kind)
            await db.commit()

        ctx.enriched_at = now_iso()
        ctx.write = {
            "units": [unit.model_dump() for unit in units],
            "degradations": ctx.degradations or None,
            "enriched_at": ctx.enriched_at,
        }


class SynthesizeStep:
    """Spawn a remote synthesis over the derived spoken paragraphs and move the item to
    generating, persisting the call handle. This is the queued phase's last step: the status
    flip to generating suspends the pipeline until a poll drives the durable phase."""

    name = "spawn"
    phase = ItemStatus.QUEUED

    def __init__(self, synthesizer: Synthesizer):
        self._synthesizer = synthesizer

    def wants(self, ctx: PipelineContext) -> bool:
        return bool(ctx.enriched_at)

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        call_id = await run_in_threadpool(
            self._synthesizer.spawn, [unit.spoken for unit in ctx.units], ctx.voice
        )
        ctx.write = {"status": ItemStatus.GENERATING, "modal_call_id": call_id}


class ResolveStep:
    """Resolve the in-flight synthesis call on poll. A still-running job leaves the item
    generating and writes nothing; a crashed job fails it with the tts: error; a finished job
    hands its result to the store step, which owns the finalize write."""

    name = "tts"
    phase = ItemStatus.GENERATING

    def __init__(self, synthesizer: Synthesizer):
        self._synthesizer = synthesizer

    def wants(self, ctx: PipelineContext) -> bool:
        return ctx.modal_call_id is not None and ctx.synthesis is None

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        call_id = ctx.modal_call_id
        if call_id is None:  # guaranteed by wants; narrows the type for the call below
            return
        status, payload = await run_in_threadpool(self._synthesizer.resolve, call_id)
        if status == ItemStatus.READY and isinstance(payload, SynthesisResult):
            ctx.synthesis = payload
        elif status == ItemStatus.FAILED:
            ctx.write = {"status": ItemStatus.FAILED, "error": f"tts: {payload}"}


class StoreStep:
    """Store the audio and join the position-keyed timeline onto the display units by index,
    then move the item to ready. The length guard fails the item on a mismatch (invariant 2);
    the timing is matched by list position, never by text, so display and timing stay aligned."""

    name = "store"
    phase = ItemStatus.GENERATING

    def wants(self, ctx: PipelineContext) -> bool:
        return ctx.synthesis is not None

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        result = ctx.synthesis
        if result is None:  # guaranteed by wants; narrows the type for the join below
            return
        base = [unit.model_dump() for unit in ctx.units]
        if len(base) != len(result.paragraphs):
            raise ValueError(
                f"alignment mismatch: {len(base)} units vs {len(result.paragraphs)} timed"
            )

        # boto3's S3 client (and the local file write behind the same seam) is synchronous and
        # blocking, so it runs off the event loop.
        await run_in_threadpool(
            audio_storage.store,
            ctx.item_id,
            audio_ext(result.format),
            base64.b64decode(result.audio_base64),
            result.format,
        )

        ctx.write = {
            "status": ItemStatus.READY,
            "duration": result.duration,
            "audio_format": result.format,
            "units": [
                {**base[p.index], "index": p.index, "start": p.start, "end": p.end}
                for p in result.paragraphs
            ],
        }

        # TTS bills on duration; record it in the same session so the cost commits with the
        # ready transition (get_db).
        await record_tts_cost(db, ctx.item_id, result.duration)
