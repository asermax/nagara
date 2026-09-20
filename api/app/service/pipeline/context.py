from dataclasses import dataclass, field

from ...models.item import ItemStatus
from ...schemas.items import Unit
from ...schemas.tts import SynthesisResult
from ..describe import ImageDescribeRequest
from ..fetch import FirecrawlUsage


@dataclass
class PipelineContext:
    """The item under construction, threaded through one ``advance`` call.

    It seeds from the row, carries the working state each step reads and writes, and holds the
    transient values that never persist — the fetched ``html``, the domain and recipe the spawn
    carries, the cost accumulators, the resolved ``synthesis`` result. ``write`` is the columns
    the current step wants persisted; the runner applies it per phase. The typed ``units`` are
    the through-line: display, spoken, and later timing ride on one list, matched by index and
    never by text (invariants 1 and 2).
    """

    item_id: str
    url: str
    voice: str
    phase: ItemStatus

    title: str | None = None
    units: list[Unit] = field(default_factory=list)
    enriched_at: str | None = None
    modal_call_id: str | None = None
    retry_count: int | None = None

    # the extraction boundary: the handle is the job id (stable across retries), the
    # domain is the final host the fetch landed on, and the pointer names the recipe
    # version this item was spawned with — moved when the job hands back a recipe.
    extraction_handle: str | None = None
    extraction_domain: str | None = None
    recipe_version_id: str | None = None

    # transient, never a column on the row
    html: str | None = None
    domain: str | None = None
    recipe: str | None = None
    image_requests: list[ImageDescribeRequest] = field(default_factory=list)
    firecrawl_usage: FirecrawlUsage | None = None
    describe_kinds: list[str] = field(default_factory=list)
    degradations: list[dict] = field(default_factory=list)
    synthesis: SynthesisResult | None = None

    # the columns the step just ran wants persisted; the runner applies and clears it
    write: dict = field(default_factory=dict)
