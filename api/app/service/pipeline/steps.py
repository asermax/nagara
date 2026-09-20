import base64

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ...config import settings
from ...helpers import now_iso
from ...models.item import ItemStatus
from ...schemas.tts import SynthesisResult
from ..cost import record_describer_cost, record_firecrawl_cost, record_tts_cost
from ..describe import enrich_with_descriptions
from ..extraction import mint_handle, resolve_extraction, spawn_extraction
from ..fetch import ExtractionError, FirecrawlFetcher
from ..images import enrich_declared_images
from ..recipes import domain_from_url, insert_recipe_version, latest_recipe
from ..storage import audio_ext, audio_storage
from ..tts import Synthesizer
from .context import PipelineContext


def _extraction_settled(ctx: PipelineContext) -> bool:
    """A queued row that is enriched, or already carries units, has no extraction work
    left: its units came from a resolved job (or a pre-deploy local run), so the queued
    phase is done and the row belongs in the generating phase."""
    return bool(ctx.enriched_at or ctx.units)


class FetchStep:
    """Fetch the URL through firecrawl and mint the extraction handle, persisting the
    handle before any spawn is attempted. The handle is the item's job id — reused from
    the row when one survives (a spawn whose outcome stayed unknown, a ceiling death
    with the job still alive), minted fresh otherwise — and it is written while the item
    is still queued so a spawn that never confirms leaves the row holding the id the
    retry re-attaches to. The billed scrape is metered on its own commit that an
    abandoned item write cannot swallow. The ``wants`` guard stays HTML-based and adds
    the units on the row: a row that already carries units (describe failed downstream,
    or a pre-deploy item enriched under the old flow) never fetches or spawns again."""

    name = "fetch"
    phase = ItemStatus.QUEUED

    def wants(self, ctx: PipelineContext) -> bool:
        return not _extraction_settled(ctx) and ctx.html is None

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        def capture(usage) -> None:
            ctx.firecrawl_usage = usage

        try:
            page = await run_in_threadpool(
                FirecrawlFetcher(settings.firecrawl_api_key, capture).fetch, ctx.url
            )
        finally:
            if ctx.firecrawl_usage is not None:
                await record_firecrawl_cost(db, ctx.item_id, ctx.firecrawl_usage)
                await db.commit()

        domain = domain_from_url(page.url)
        ctx.html = page.html
        ctx.extraction_domain = domain

        current = await latest_recipe(db, domain)
        if current is not None:
            ctx.recipe = current.script
            ctx.recipe_version_id = current.id

        if ctx.extraction_handle is None:
            # The mint is the only write: a reused handle writes nothing, so a re-run
            # over an already-spawned job is not mistaken for an abandoned write.
            ctx.extraction_handle = mint_handle(ctx.item_id, ctx.retry_count)
            ctx.write = {
                "extraction_handle": ctx.extraction_handle,
                "extraction_domain": domain,
            }


class SpawnStep:
    """Hand the fetched HTML to the extraction service and move the item to generating,
    persisting the handle and the recipe version it was spawned with. 201 (created) and
    409 (the id already exists — the re-attach path) both proceed: the handle rule makes
    them the same outcome. A too-large html and an unreachable service both fail the
    item with this step's ``extraction:`` prefix; the handle stays on the row either
    way, so a retry re-spawns — and may succeed when the failure was reachability,
    while a too-large article fails the same way again."""

    name = "extraction"
    phase = ItemStatus.QUEUED

    def wants(self, ctx: PipelineContext) -> bool:
        return not _extraction_settled(ctx) and ctx.html is not None

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        html = ctx.html
        if html is None or ctx.extraction_handle is None or ctx.extraction_domain is None:
            return  # guaranteed by wants plus FetchStep's mint; narrows the types
        await spawn_extraction(html, ctx.recipe, ctx.extraction_handle, ctx.extraction_domain)
        ctx.write = {
            "status": ItemStatus.GENERATING,
            "recipe_version_id": ctx.recipe_version_id,
        }


class PromoteStep:
    """Move a queued row that has no queued work left to generating: enriched rows have
    none — describe and synthesis run in the generating phase, on poll — and rows that
    already carry units have none either, so the retry of a describe-failure or a
    pre-deploy mid-enrichment row re-enters the pipeline here at zero extraction cost.

    The trade this step accepts: an image the first attempt never described keeps the
    alt-or-floor spoken form it was acquired with, because the describe context lives
    only in the advance that resolved extraction. Rebuilding it needs the alt stored on
    the unit, which the boundary does not carry — a product decision, not a review fix."""

    name = "promote"
    phase = ItemStatus.QUEUED

    def wants(self, ctx: PipelineContext) -> bool:
        return _extraction_settled(ctx)

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        ctx.write = {"status": ItemStatus.GENERATING}


class ExtractionResolveStep:
    """Resolve the extraction job on poll and map the boundary's states to outcomes.

    ``queued`` and ``running`` are holds: nothing is written and the item stays
    generating, the ceiling standing guard over the hold. ``not_article`` fails the item
    with the handle retained, so a retry re-attaches and the verdict stands. ``error``
    fails it with the handle cleared, because that is the one terminal whose instance
    would hand back the same failure — the retry mints a new id. ``complete`` persists
    the title and the units (deriving the spoken form from the display markdown, so one
    extraction stays the source of truth), inserts the job's recipe as the domain's next
    version when it carried one, and clears the handle so later polls resolve synthesis,
    never the job again."""

    name = "extraction"
    phase = ItemStatus.GENERATING

    def wants(self, ctx: PipelineContext) -> bool:
        return ctx.extraction_handle is not None

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        handle = ctx.extraction_handle
        if handle is None:  # guaranteed by wants; narrows the type for the call below
            return
        status = await resolve_extraction(handle)

        if status.state in ("queued", "running"):
            return

        if status.state == "not_article":
            raise ExtractionError("extraction: not an article")

        if status.state == "error":
            ctx.write = {
                "status": ItemStatus.FAILED,
                "error": f"extraction: {status.error}",
                "extraction_handle": None,
            }
            return

        units, degradations, requests = await enrich_declared_images(status.units or [], status.title)
        if not units:
            raise ExtractionError("extraction: no surviving units")

        ctx.units = units
        ctx.image_requests = requests
        ctx.degradations += degradations

        ctx.write = {
            "title": status.title,
            "units": [unit.model_dump() for unit in units],
            "extraction_handle": None,
        }

        domain = ctx.extraction_domain
        if status.recipe is not None and domain is not None:
            # The job authored or revised the domain's recipe: a pure insert as the next
            # version, and the item's pointer moves to it.
            version = await insert_recipe_version(db, domain, status.recipe)
            ctx.recipe_version_id = version.id
            ctx.write["recipe_version_id"] = version.id


class DescribeStep:
    """Describe code blocks and case-3 images against one shared budget, then mark enrichment
    finished. The describer calls are metered on their own commit; ``enriched_at`` is the flag a
    retry reads to re-enter at the generating phase without re-fetching, so it is written here
    with the final unit list once every unit has resolved its spoken form."""

    name = "enrichment"
    phase = ItemStatus.GENERATING

    def wants(self, ctx: PipelineContext) -> bool:
        # A cleared handle is the row's record that extraction resolved: it is set at
        # the mint and cleared in the same write that lands the units, so this gates on
        # the state itself rather than on a units-present proxy for it.
        return not ctx.enriched_at and ctx.extraction_handle is None

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
        ctx.units = units
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
    """Spawn a remote synthesis over the derived spoken paragraphs and persist the call
    handle. The item is already generating — extraction resolved and enrichment finished
    — so this step only records the handle; the status flip that once rode here belongs
    to the spawn and promote steps of the queued phase."""

    name = "spawn"
    phase = ItemStatus.GENERATING

    def __init__(self, synthesizer: Synthesizer):
        self._synthesizer = synthesizer

    def wants(self, ctx: PipelineContext) -> bool:
        return bool(ctx.enriched_at) and ctx.modal_call_id is None

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None:
        call_id = await run_in_threadpool(
            self._synthesizer.spawn, [unit.spoken for unit in ctx.units], ctx.voice
        )
        ctx.write = {"modal_call_id": call_id}


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
