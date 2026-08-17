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
from ..service.describe import ImageDescribeRequest
from ..service.extract import _is_cruft
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
    title: str | None,
    units: Sequence[Unit],
    item_id: str,
) -> tuple[list[Unit], list[dict], list[ImageDescribeRequest]]:
    """Select, acquire, and interleave article images.

    Returns (enriched_units, degradation_dicts, image_describe_requests). The requests are the
    case-3 images (no caption, no good alt): the describer fan-out fills them in against the
    shared budget, and each request's index points into the returned unit list.
    """
    candidates = select_article_images(html, units, url)

    if not candidates:
        return list(units), [], []

    title_norm = (title or "").strip().lower()
    positioned, degradations, describe_ctx = await acquire_images(candidates, item_id, title_norm)

    enriched = interleave_image_units(units, positioned)

    requests: list[ImageDescribeRequest] = []
    for i, unit in enumerate(enriched):
        context = describe_ctx.get(id(unit))
        if context is not None:
            alt, image = context
            requests.append(ImageDescribeRequest(index=i, alt=alt, image=image))

    return enriched, [d.to_dict() for d in degradations], requests


# ---------------------------------------------------------------------------
# Image selection — DOM containment + og:image
# ---------------------------------------------------------------------------


@dataclass
class ImageCandidate:
    src: str
    alt: str
    insert_after: int
    caption: str = ""


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
        caption = _find_caption(img)

        img_path = root.getpath(img)
        img_doc_idx = doc_order.get(img_path, float("inf"))

        insert_after = -1
        for anchor_doc_idx, unit_idx in anchor_positions:
            if anchor_doc_idx < img_doc_idx:
                insert_after = unit_idx
            else:
                break

        candidates.append(
            ImageCandidate(
                src=resolved, alt=alt, insert_after=insert_after, caption=caption
            )
        )

    return candidates


# Figure captions ride on a per-CMS class on the caption-text leaf, never on the wrapper.
# Matching the leaf excludes the credit line by construction: the New Yorker keeps
# "Photograph by ... / Courtesy ©" in a sibling ``CaptionCredit`` span, and a heuristic over
# any class containing "caption" would swallow both that credit span (its class lowercases to
# contain "caption") and the ``CaptionWrapper`` that concatenates caption and credit. A leaf
# selector per CMS is exact; adding a publisher is one entry here.
_CAPTION_LEAF_CLASSES = ("caption__text", "image-caption")
_CAPTION_FIGURE_MAX_CLIMB = 8


def _find_caption(img: HtmlElement) -> str:
    """Return the author's figure caption for ``img``, or ``""`` when there is none.

    Anchored on the image's enclosing ``<figure>``, so a caption never leaks from a
    neighbouring image, and reading the caption-text leaf leaves the sibling credit span out.
    """
    figure = _enclosing_figure(img)

    if figure is None:
        return ""

    for el in figure.iterdescendants():
        if not isinstance(el.tag, str):
            continue

        cls = el.get("class") or ""

        if any(token in cls for token in _CAPTION_LEAF_CLASSES):
            return re.sub(r"\s+", " ", el.text_content()).strip()

    return ""


def _enclosing_figure(img: HtmlElement) -> HtmlElement | None:
    el = img

    for _ in range(_CAPTION_FIGURE_MAX_CLIMB):
        el = el.getparent()

        if el is None:
            return None

        if el.tag == "figure":
            return el

    return None


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


def _image_spoken(caption: str, alt: str) -> str:
    """Spoken form of an image, highest-signal source first.

    A present caption is the author's own prose about the image, so it wins outright and
    short-circuits the rest of the precedence: the describer is never reached for a
    captioned image.

    This is the precedence's fallback form for every case: caption (1), verbatim alt (2 and,
    on a describer failure, 4), then the floor (5). A case-3 image carries this as its spoken
    form until a successful describe overwrites it — so a failed or over-budget describe is
    never silent, it simply keeps the fallback already here.
    """
    if caption:
        return f"Image: {caption}"

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


def _needs_describe(caption: str, alt: str, title_norm: str) -> bool:
    """True when the image reaches the describer (case 3): no caption and no good alt."""
    if caption:
        return False

    return not _is_good_alt(alt, title_norm)


def _is_good_alt(alt: str, title_norm: str) -> bool:
    """True when alt is spoken verbatim (case 2), False when it goes to the describer (case 3).

    Conservative on purpose: alt is trusted only when it reads as a sentence, is not the article
    title (the same title-echo check the extractor's cruft trim uses), and clears a small CMS
    denylist. Everything else — empty, SEO keyword soup, a title-as-alt, a subscribe prompt, a
    filename — is sent to the describer. This inverts the bake-off's "alt as context, never
    verbatim" on purpose: no clean heuristic separates good alt from bad, so the denylist is the
    line, at the cost of a maintained list a novel boilerplate phrase can slip past.
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


async def acquire_images(
    candidates: list[ImageCandidate],
    item_id: str,
    title_norm: str,
) -> tuple[list[tuple[int, ImageUnit]], list[Degradation], dict[int, tuple[str, bytes]]]:
    """Download, validate, and store article images.

    Returns (positioned_units, degradations, describe_ctx). positioned_units is a list of
    (insert_after, ImageUnit) pairs; describe_ctx maps a case-3 image unit's `id()` to its
    (alt, WebP bytes), the context the describer fan-out needs to fill it in.
    """
    host_semaphores: dict[str, asyncio.Semaphore] = defaultdict(
        lambda: asyncio.Semaphore(settings.image_fetch_per_host)
    )
    global_sem = asyncio.Semaphore(settings.image_fetch_concurrency)

    async def process_one(
        candidate: ImageCandidate,
    ) -> tuple[tuple[int, ImageUnit] | None, Degradation | None, tuple[str, bytes] | None]:
        try:
            image_hash, webp = await _fetch_and_store(
                candidate.src, host_semaphores, global_sem
            )
        except _AcquisitionError as e:
            return None, Degradation(type="image", url=candidate.src, reason=str(e)), None

        unit = ImageUnit(
            type="image",
            display=candidate.caption or candidate.alt,
            spoken=_image_spoken(candidate.caption, candidate.alt),
            image=image_hash,
        )
        context = (
            (candidate.alt.strip(), webp)
            if _needs_describe(candidate.caption, candidate.alt, title_norm)
            else None
        )
        return (candidate.insert_after, unit), None, context

    results = await asyncio.gather(
        *(process_one(c) for c in candidates),
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
