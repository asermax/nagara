from typing import Annotated, Literal, Union, get_args

from pydantic import BaseModel, Field

# The five states the extraction service's GET answers, and the three unit kinds its
# complete output carries. Both mirror the boundary contract verbatim (no StrEnum, per
# the project's no-enum rule): the client returns the state unmodified and the pipeline
# maps it to outcomes. The runtime tuple derives from the Literal so the two cannot
# drift, matching the cost-ledger types.
ExtractionState = Literal["queued", "running", "complete", "not_article", "error"]
EXTRACTION_STATES: tuple[ExtractionState, ...] = get_args(ExtractionState)

# The caller-chosen instance id the service accepts, so the API's itm_ ids (and their
# retry suffixes) are legal unchanged.
_JOB_ID_PATTERN = r"^[a-zA-Z0-9_][a-zA-Z0-9-_]*$"


class CreateJobPayload(BaseModel):
    html: str
    job_id: str = Field(pattern=_JOB_ID_PATTERN)
    domain: str
    recipe: str | None = None


class _ServiceUnitBase(BaseModel):
    display: str


class ServiceParagraphUnit(_ServiceUnitBase):
    type: Literal["paragraph"]


class ServiceCodeUnit(_ServiceUnitBase):
    type: Literal["code"]


class ServiceImageUnit(_ServiceUnitBase):
    type: Literal["image"]
    src: str
    alt: str


ServiceUnit = Annotated[
    Union[ServiceParagraphUnit, ServiceCodeUnit, ServiceImageUnit],
    Field(discriminator="type"),
]


class JobStatus(BaseModel):
    """One GET /jobs/{job_id} answer: the state plus the members that apply to it.

    Absent members mean not applicable, never empty, so every member but the state is
    optional. No spoken form crosses the boundary — the API derives it (invariant 1).
    """

    state: ExtractionState
    title: str | None = None
    units: list[ServiceUnit] | None = None
    recipe: str | None = None
    error: str | None = None
