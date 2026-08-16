"""Article image selection and acquisition.

Finds images that belong to an article's own body by probing back into the
original HTML tree, downloads them, and produces ImageUnits ready for the
unit list.
"""

import asyncio
import re
import urllib.parse
from base64 import b64decode
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO

import httpx
from lxml import html as lhtml
from lxml.html import HtmlElement
from PIL import Image
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..schemas.items import ImageUnit, Unit
from ..service.storage import image_storage

_SKIP_TAGS = frozenset({"script", "style", "noscript", "template"})

MIN_IMAGE_DIMENSION = 200
IMAGE_FETCH_TIMEOUT = 10.0
IMAGE_MAX_BYTES = 10 * 1024 * 1024

_SVG_RASTERISE_WIDTH = 768

try:
    import cairosvg

    _HAS_CAIROSVG = True
except Exception:
    # A missing cairosvg raises ImportError; a cairosvg present without the cairo system
    # library raises OSError from cairocffi's dlopen at import time. Both mean SVG cannot be
    # rasterised, so both degrade the same way (SVG units drop) rather than crash the process.
    _HAS_CAIROSVG = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def enrich_with_images(
    html: str,
    url: str,
    units: Sequence[Unit],
    item_id: str,
) -> tuple[list[Unit], list[dict]]:
    """Select, acquire, and interleave article images.

    Returns (enriched_units, degradation_dicts).
    """
    candidates = select_article_images(html, units, url)

    if not candidates:
        return list(units), []

    positioned, degradations = await acquire_images(candidates, item_id)

    enriched = interleave_image_units(units, positioned)

    return enriched, [d.to_dict() for d in degradations]


# ---------------------------------------------------------------------------
# Image selection — DOM containment + og:image
# ---------------------------------------------------------------------------


@dataclass
class ImageCandidate:
    src: str
    alt: str
    insert_after: int


def select_article_images(
    html: str,
    units: Sequence[Unit],
    url: str,
) -> list[ImageCandidate]:
    """Find article images via DOM containment + og:image."""
    tree = lhtml.fromstring(html)

    anchors = _find_anchors(tree, units)
    container = _find_container(tree, anchors) if anchors else None

    candidates: list[ImageCandidate] = []
    seen: set[str] = set()

    for og_url in _og_image_urls(tree, url):
        if og_url not in seen:
            seen.add(og_url)
            candidates.append(ImageCandidate(src=og_url, alt="", insert_after=-1))

    if container is not None:
        for img_candidate in _collect_container_images(tree, container, anchors, url):
            if img_candidate.src not in seen:
                seen.add(img_candidate.src)
                candidates.append(img_candidate)

    return candidates


def _find_anchors(
    tree,
    units: Sequence[Unit],
) -> list[tuple[HtmlElement, int]]:
    """Match the longest units to DOM elements by probing their spoken text.

    Returns (element, unit_index) pairs. The deepest element whose
    text_content holds the probe is chosen, so a ``<p>`` wins over its
    containing ``<div>``.
    """
    anchors = []

    for idx in sorted(
        range(len(units)), key=lambda i: len(units[i].spoken), reverse=True
    )[:25]:
        probe = re.sub(r"\s+", " ", units[idx].spoken)[:40].strip()

        if len(probe) < 25:
            continue

        best_depth = -1
        best_el = None

        for el in tree.iter():
            if not isinstance(el.tag, str) or el.tag in _SKIP_TAGS:
                continue

            try:
                text = re.sub(r"\s+", " ", el.text_content())
            except Exception:
                continue

            if probe[:25] in text:
                depth = sum(1 for _ in el.iterancestors())

                if depth > best_depth:
                    best_depth = depth
                    best_el = el

        if best_el is not None:
            anchors.append((best_el, idx))

    return anchors


def _find_container(tree, anchors: list[tuple[HtmlElement, int]]):
    """Deepest element holding >= 80% of anchors."""
    if not anchors:
        return None

    root = tree.getroottree()
    holds: Counter[str] = Counter()

    for el, _ in anchors:
        for anc in el.iterancestors():
            holds[root.getpath(anc)] += 1

    need = max(2, int(len(anchors) * 0.8))
    winners = [path for path, count in holds.items() if count >= need]

    if not winners:
        return None

    deepest_path = max(winners, key=lambda p: p.count("/"))
    return root.xpath(deepest_path)[0]


def _og_image_urls(tree, base_url: str) -> list[str]:
    urls = []

    for content in tree.xpath("//meta[@property='og:image']/@content")[:1]:
        resolved = urllib.parse.urljoin(base_url, content)
        if resolved:
            urls.append(resolved)

    return urls


def _collect_container_images(
    tree,
    container,
    anchors: list[tuple[HtmlElement, int]],
    base_url: str,
) -> list[ImageCandidate]:
    """Collect images from the article container with document-order positions."""
    root = tree.getroottree()

    doc_order: dict[str, int] = {}
    for i, el in enumerate(container.iter()):
        doc_order[root.getpath(el)] = i

    anchor_positions = sorted(
        [
            (doc_order.get(root.getpath(el), -1), unit_idx)
            for el, unit_idx in anchors
            if doc_order.get(root.getpath(el), -1) >= 0
        ],
        key=lambda x: x[0],
    )

    candidates = []

    for img in container.iter("img"):
        src = img.get("src") or img.get("data-src") or ""

        if not src:
            continue

        resolved = _resolve_src(src, base_url)

        if not resolved:
            continue

        alt = (img.get("alt") or "").strip()

        img_path = root.getpath(img)
        img_doc_idx = doc_order.get(img_path, float("inf"))

        insert_after = -1
        for anchor_doc_idx, unit_idx in anchor_positions:
            if anchor_doc_idx < img_doc_idx:
                insert_after = unit_idx
            else:
                break

        candidates.append(
            ImageCandidate(src=resolved, alt=alt, insert_after=insert_after)
        )

    return candidates


def _resolve_src(src: str, base_url: str) -> str:
    if src.startswith("data:"):
        return src

    return urllib.parse.urljoin(base_url, src)


# ---------------------------------------------------------------------------
# Image acquisition — download, validate, rasterise, store
# ---------------------------------------------------------------------------


@dataclass
class Degradation:
    type: str
    url: str
    reason: str

    def to_dict(self) -> dict:
        return {"type": self.type, "url": self.url, "reason": self.reason}


class _AcquisitionError(Exception):
    pass


async def acquire_images(
    candidates: list[ImageCandidate],
    item_id: str,
) -> tuple[list[tuple[int, ImageUnit]], list[Degradation]]:
    """Download, validate, and store article images.

    Returns (positioned_units, degradations) where positioned_units is a list
    of (insert_after, ImageUnit) pairs.
    """
    host_semaphores: dict[str, asyncio.Semaphore] = defaultdict(
        lambda: asyncio.Semaphore(settings.image_fetch_per_host)
    )
    global_sem = asyncio.Semaphore(settings.image_fetch_concurrency)

    async def process_one(
        candidate: ImageCandidate,
    ) -> tuple[tuple[int, ImageUnit] | None, Degradation | None]:
        try:
            image_hash = await _fetch_and_store(
                candidate.src, host_semaphores, global_sem
            )
        except _AcquisitionError as e:
            return None, Degradation(
                type="image", url=candidate.src, reason=str(e)
            )

        spoken = (
            f"Image: {candidate.alt}" if candidate.alt else "Image with no description."
        )
        unit = ImageUnit(
            type="image",
            display=candidate.alt,
            spoken=spoken,
            image=image_hash,
        )
        return (candidate.insert_after, unit), None

    results = await asyncio.gather(
        *(process_one(c) for c in candidates),
        return_exceptions=True,
    )

    units: list[tuple[int, ImageUnit]] = []
    degradations: list[Degradation] = []

    for result in results:
        if isinstance(result, BaseException):
            continue

        positioned_unit, degradation = result

        if positioned_unit is not None:
            units.append(positioned_unit)

        if degradation is not None:
            degradations.append(degradation)

    return units, degradations


async def _fetch_and_store(
    src: str,
    host_semaphores: dict[str, asyncio.Semaphore],
    global_sem: asyncio.Semaphore,
) -> str:
    if src.startswith("data:"):
        raw = _decode_data_uri(src)
    else:
        raw = await _download_image(src, host_semaphores, global_sem)

    if _is_svg(raw):
        raw = _rasterise_svg(raw)
    else:
        _check_dimensions(raw)

    return await run_in_threadpool(image_storage.store, raw)


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


# ---------------------------------------------------------------------------
# Unit interleaving
# ---------------------------------------------------------------------------


def interleave_image_units(
    text_units: Sequence[Unit],
    positioned_images: list[tuple[int, ImageUnit]],
) -> list[Unit]:
    """Insert image units at their document-order positions in the text unit list."""
    if not positioned_images:
        return list(text_units)

    by_position: dict[int, list[ImageUnit]] = defaultdict(list)

    for insert_after, unit in positioned_images:
        by_position[insert_after].append(unit)

    result: list[Unit] = []

    result.extend(by_position.get(-1, []))

    for i, unit in enumerate(text_units):
        result.append(unit)
        result.extend(by_position.get(i, []))

    return result
