"""The extraction-service client: spawn at the source step, resolve on poll.

A thin client over the boundary contract (docs/technical-design/extraction-service.md):
``spawn`` posts the fetched HTML, the domain's current recipe or none, and the
caller-chosen job id; ``resolve`` reads one job back. The client translates nothing —
it returns the boundary's status unmodified and lets the pipeline map states to
outcomes, per the design's calling side. 201 and 409 are both an accepted spawn (a
fresh create and a re-attach to the id that already exists); 413 is surfaced as a
distinct exception so the caller can fail the item without retrying; every network
failure raises the HTTP library's own error for the step to name.
"""

import httpx

from ..config import settings
from ..schemas.extraction import CreateJobPayload, JobStatus

_TIMEOUT = httpx.Timeout(30.0)


class HtmlTooLarge(Exception):
    """The fetched HTML exceeds the service's ~1 MiB cap, rejected with no job created."""


def mint_handle(item_id: str, retry_count: int | None) -> str:
    """The extraction handle: the item id, suffixed per retry once an id was reminted.

    The handle is stable across retries — a retried item re-attaches to the same job —
    and only the previous job's ``error`` terminal clears it, because that is the one
    terminal whose instance would hand back the same failure. The suffix rides the
    retry count, which advances on every attempt, so a reminted id never collides with
    a job from an earlier attempt while its retention window is open.
    """
    return item_id if not retry_count else f"{item_id}-{retry_count}"


def _access_headers() -> dict[str, str]:
    if settings.cf_access_client_id and settings.cf_access_client_secret:
        return {
            "CF-Access-Client-Id": settings.cf_access_client_id,
            "CF-Access-Client-Secret": settings.cf_access_client_secret,
        }
    return {}


async def spawn_extraction(html: str, recipe: str | None, job_id: str, domain: str) -> bool:
    """Hand one article to the service. Returns True when the job was created (201),
    False when the id already exists (409) — the re-attach path."""
    if not settings.cloudflare_extraction_url:
        raise RuntimeError("extraction service URL is not configured (NAGARA_CLOUDFLARE_EXTRACTION_URL)")

    payload = CreateJobPayload(html=html, recipe=recipe, job_id=job_id, domain=domain)
    async with httpx.AsyncClient(
        base_url=settings.cloudflare_extraction_url,
        headers=_access_headers(),
        timeout=_TIMEOUT,
    ) as client:
        response = await client.post("/jobs", json=payload.model_dump(exclude_none=True))

    if response.status_code in (201, 409):
        return response.status_code == 201
    if response.status_code == 413:
        raise HtmlTooLarge()
    response.raise_for_status()
    raise RuntimeError(f"unexpected spawn status {response.status_code}")


async def resolve_extraction(job_id: str) -> JobStatus:
    """Read one job back. The boundary answers 200 with the state in the body; anything
    else is a service-side failure and raises."""
    if not settings.cloudflare_extraction_url:
        raise RuntimeError("extraction service URL is not configured (NAGARA_CLOUDFLARE_EXTRACTION_URL)")

    async with httpx.AsyncClient(
        base_url=settings.cloudflare_extraction_url,
        headers=_access_headers(),
        timeout=_TIMEOUT,
    ) as client:
        response = await client.get(f"/jobs/{job_id}")

    response.raise_for_status()
    return JobStatus.model_validate(response.json())
