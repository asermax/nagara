"""Article image acquisition for recipe-declared images.

The recipe declares which images belong to the article (a service image unit's ``src``
and ``alt``); this module acquires them — download, validate, rasterise, store — and
builds the image units for the resolved list, dropping any image that will not acquire
from both lists with a recorded degradation. Selection by DOM containment is retired
with the local extractor: the recipe's declaration is the selection.
"""

import asyncio
import re
import urllib.parse
from base64 import b64decode
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO

import httpx
from PIL import Image
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..schemas.extraction import ServiceUnit
from ..schemas.items import CodeUnit, ImageUnit, ParagraphUnit, Unit
from ..service.describe import ImageDescribeRequest
from ..service.extract import _is_cruft, _to_spoken
from ..service.storage import image_storage

MIN_IMAGE_DIMENSION = 200
IMAGE_FETCH_TIMEOUT = 10.0
IMAGE_MAX_BYTES = 10 * 1024 * 1024

_SVG_RASTERISE_WIDTH = 768

try:
    import cairosvg

    _HAS_CAIROSVG = True
except Exception:
    # A missing cairosvg raises ImportError; a cairosvg present without the cairo system
    # library raises OSError from cairocffi's dlopen at import time. Both mean SVG cannot
    # be rasterised, so both degrade the same way (SVG units drop) rather than crash the process.
    _HAS_CAIROSVG = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def enrich_declared_images(
    service_units: Sequence[ServiceUnit],
    title: str | None,
) -> tuple[list[Unit], list[dict], list[ImageDescribeRequest]]:
    """Convert the service's units into the pipeline's, acquiring the declared images.

    Text units derive their spoken form from their display markdown (invariant 1: no
    spoken form crosses the boundary); each declared image is downloaded, validated, and
    stored, its hash becoming the unit's image reference. An image that will not acquire
    is dropped from the list with a degradation rather than failing the item; its spoken
    form comes from the alt, and the describe precedence decides whether the describer
    improves it. Returns (units, degradations, image_describe_requests).
    """
    title_norm = (title or "").strip().lower()
    text_units: list[Unit] = []
    declared: list[_DeclaredImage] = []

    for service_unit in service_units:
        if service_unit.type == "image":
            declared.append(_DeclaredImage(src=service_unit.src, alt=service_unit.alt, display=service_unit.display, after=len(text_units) - 1))
            continue

        spoken = _to_spoken(service_unit.display)
        if not spoken:
            # A unit whose spoken form strips to empty is dropped from the one list, so
            # display and timing leave together (invariant 2).
            continue
        if service_unit.type == "code":
            text_units.append(CodeUnit(type="code", display=service_unit.display, spoken=spoken))
        else:
            text_units.append(ParagraphUnit(type="paragraph", display=service_unit.display, spoken=spoken))

    positioned, degradations, describe_ctx = await _acquire_declared(declared, title_norm)

    # Interleave at the declared document-order positions: an image leading the article
    # (after == -1) goes before every text unit; the rest follow the text unit they came
    # after, so the resolved list keeps the recipe's order.
    by_position: dict[int, list[ImageUnit]] = defaultdict(list)
    for after, unit in positioned:
        by_position[after].append(unit)

    units: list[Unit] = list(by_position.get(-1, []))
    for i, unit in enumerate(text_units):
        units.append(unit)
        units.extend(by_position.get(i, []))

    requests: list[ImageDescribeRequest] = []
    for i, unit in enumerate(units):
        context = describe_ctx.get(id(unit))
        if context is not None:
            alt, image = context
            requests.append(ImageDescribeRequest(index=i, alt=alt, image=image))

    return units, [d.to_dict() for d in degradations], requests


# ---------------------------------------------------------------------------
# Acquisition — download, validate, rasterise, store
# ---------------------------------------------------------------------------


@dataclass
class _DeclaredImage:
    src: str
    alt: str
    display: str
    after: int


@dataclass
class Degradation:
    type: str
    url: str
    reason: str

    def to_dict(self) -> dict:
        return {"type": self.type, "url": self.url, "reason": self.reason}


class _AcquisitionError(Exception):
    pass


def _image_spoken(alt: str) -> str:
    """Spoken form of a declared image: the author's alt, else the honest floor. This is
    the precedence's fallback form: a non-empty alt is spoken verbatim (and kept on a
    describer failure), a case-3 image carries this until a successful describe
    overwrites it, and the floor keeps the window from being silent."""
    if alt:
        return f"Image: {alt}"

    return "Image with no description."


# CMS boilerplate that reads as a sentence but says nothing about the image. A phrase here sends
# the alt to the describer (case 3) instead of speaking it verbatim (case 2): it is the line the
# quest draws between "Image of tank rolling over a world map" (kept) and "This article appears in
# the October 2023 issue. Subscribe to WIRED." (described), both grammatical sentences.
_ALT_DENYLIST = ("subscribe", "appears in", "courtesy", "photograph by", "click")

# A filename or bare image reference is never a description: "IMG_1234.jpg", "hero-image.png".
_ALT_FILENAME = re.compile(r"\.(jpe?g|png|gif|webp|svg|avif|bmp|tiff?)\b", re.IGNORECASE)


def _needs_describe(alt: str, title_norm: str) -> bool:
    """True when the image reaches the describer (case 3): no good alt."""
    return not _is_good_alt(alt, title_norm)


def _is_good_alt(alt: str, title_norm: str) -> bool:
    """True when alt is spoken verbatim (case 2), False when it goes to the describer (case 3).

    Conservative on purpose: alt is trusted only when it reads as a sentence, is not the article
    title (the same title-echo check the extractor's cruft trim uses), and clears a small CMS
    denylist. Everything else — empty, SEO keyword soup, a title-as-alt, a subscribe prompt, a
    filename — is sent to the describer.
    """
    alt = alt.strip()

    if not alt:
        return False

    if _is_cruft(alt, title_norm):
        return False

    low = alt.lower()
    if any(phrase in low for phrase in _ALT_DENYLIST):
        return False

    if _ALT_FILENAME.search(alt):
        return False

    return _reads_as_sentence(alt)


def _reads_as_sentence(alt: str) -> bool:
    """A light grammaticality test: several words, and not comma-separated keyword soup."""
    if len(alt.split()) < 3:
        return False

    fragments = [fragment for fragment in alt.split(",") if fragment.strip()]
    if len(fragments) >= 3 and all(len(fragment.split()) <= 2 for fragment in fragments):
        return False

    return True


async def _acquire_declared(
    declared: list[_DeclaredImage],
    title_norm: str,
) -> tuple[list[tuple[int, ImageUnit]], list[Degradation], dict[int, tuple[str, bytes]]]:
    """Download, validate, and store the declared images.

    Returns (positioned_units, degradations, describe_ctx). positioned_units is a list of
    (after, ImageUnit) pairs; describe_ctx maps a case-3 image unit's `id()` to its
    (alt, WebP bytes), the context the describer fan-out needs to fill it in.
    """
    host_semaphores: dict[str, asyncio.Semaphore] = defaultdict(
        lambda: asyncio.Semaphore(settings.image_fetch_per_host)
    )
    global_sem = asyncio.Semaphore(settings.image_fetch_concurrency)

    async def process_one(
        image: _DeclaredImage,
    ) -> tuple[tuple[int, ImageUnit] | None, Degradation | None, tuple[str, bytes] | None]:
        try:
            image_hash, webp = await _fetch_and_store(
                image.src, host_semaphores, global_sem
            )
        except _AcquisitionError as e:
            return None, Degradation(type="image", url=image.src, reason=str(e)), None

        unit = ImageUnit(
            type="image",
            display=image.display,
            spoken=_image_spoken(image.alt),
            image=image_hash,
        )
        context = (
            (image.alt.strip(), webp)
            if _needs_describe(image.alt, title_norm)
            else None
        )
        return (image.after, unit), None, context

    results = await asyncio.gather(
        *(process_one(image) for image in declared),
        return_exceptions=True,
    )

    units: list[tuple[int, ImageUnit]] = []
    degradations: list[Degradation] = []
    describe_ctx: dict[int, tuple[str, bytes]] = {}

    for result in results:
        if isinstance(result, BaseException):
            continue

        positioned_unit, degradation, context = result

        if positioned_unit is not None:
            units.append(positioned_unit)
            if context is not None:
                describe_ctx[id(positioned_unit[1])] = context

        if degradation is not None:
            degradations.append(degradation)

    return units, degradations, describe_ctx


async def _fetch_and_store(
    src: str,
    host_semaphores: dict[str, asyncio.Semaphore],
    global_sem: asyncio.Semaphore,
) -> tuple[str, bytes]:
    if src.startswith("data:"):
        raw = _decode_data_uri(src)
    else:
        raw = await _download_image(src, host_semaphores, global_sem)

    if _is_svg(raw):
        raw = _rasterise_svg(raw)
    else:
        _check_dimensions(raw)

    return await run_in_threadpool(image_storage.store_encoded, raw)


async def _download_image(
    url: str,
    host_semaphores: dict[str, asyncio.Semaphore],
    global_sem: asyncio.Semaphore,
) -> bytes:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    host_sem = host_semaphores[host]

    async with global_sem, host_sem:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=IMAGE_FETCH_TIMEOUT
        ) as client:
            try:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    chunks: list[bytes] = []
                    total = 0

                    async for chunk in response.aiter_bytes():
                        total += len(chunk)

                        if total > IMAGE_MAX_BYTES:
                            raise _AcquisitionError("too large")

                        chunks.append(chunk)

                    return b"".join(chunks)
            except httpx.HTTPStatusError as e:
                raise _AcquisitionError(str(e.response.status_code)) from e
            except httpx.HTTPError as e:
                raise _AcquisitionError("timeout") from e
            except _AcquisitionError:
                raise


def _decode_data_uri(src: str) -> bytes:
    try:
        _, rest = src.split(",", 1)
        return b64decode(rest)
    except Exception as e:
        raise _AcquisitionError(f"undecodable data URI: {e}") from e


def _is_svg(data: bytes) -> bool:
    return b"<svg" in data[:500].lower()


def _rasterise_svg(data: bytes) -> bytes:
    if not _HAS_CAIROSVG:
        raise _AcquisitionError("svg rasterise failed")

    try:
        return cairosvg.svg2png(
            bytestring=data, output_width=_SVG_RASTERISE_WIDTH
        )
    except Exception as e:
        raise _AcquisitionError("svg rasterise failed") from e


def _check_dimensions(raw: bytes) -> None:
    try:
        with Image.open(BytesIO(raw)) as img:
            w, h = img.size
    except Exception as e:
        raise _AcquisitionError("undecodable") from e

    if min(w, h) < MIN_IMAGE_DIMENSION:
        raise _AcquisitionError(f"too small ({w}x{h})")
