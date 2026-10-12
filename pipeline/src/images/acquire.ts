import {
  type CodeUnit,
  DEGRADATION_REASON,
  type Degradation,
  type DegradationReason,
  type ImageUnit,
  imageKey,
  type ParagraphUnit,
  type Unit,
} from "@nagara/common";
import type { DeclaredImage } from "../spoken/typed-units.ts";
import { imageSpoken } from "./alt.ts";
import { semaphore } from "./semaphore.ts";
import { isSvg, SVG_CONTENT_TYPE, stripScripts } from "./svg.ts";

const MIN_IMAGE_DIMENSION = 200;
const IMAGE_FETCH_TIMEOUT_MS = 10_000;
const IMAGE_MAX_BYTES = 10 * 1024 * 1024;

type Acquired = { unit: ImageUnit; after: number };

class AcquisitionFailure extends Error {
  constructor(readonly reason: DegradationReason) {
    super(reason);
  }
}

// Read in chunks so an oversized image is refused at the cap instead of after buffering it whole.
const readCapped = async (body: ReadableStream<Uint8Array>) => {
  const chunks: Uint8Array[] = [];
  let total = 0;

  for await (const chunk of body) {
    total += chunk.byteLength;

    if (total > IMAGE_MAX_BYTES) {
      throw new AcquisitionFailure(DEGRADATION_REASON.undecodable);
    }

    chunks.push(chunk);
  }

  return new Uint8Array(await new Blob(chunks).arrayBuffer());
};

const download = async (url: string) => {
  let response: Response;

  try {
    response = await fetch(url, { signal: AbortSignal.timeout(IMAGE_FETCH_TIMEOUT_MS) });
  } catch {
    throw new AcquisitionFailure(DEGRADATION_REASON.timeout);
  }

  if (!response.ok || response.body == null) {
    throw new AcquisitionFailure(DEGRADATION_REASON.notFound);
  }

  try {
    return await readCapped(response.body);
  } catch (error) {
    throw error instanceof AcquisitionFailure
      ? error
      : new AcquisitionFailure(DEGRADATION_REASON.timeout);
  }
};

const decodeDataUri = (src: string) => {
  try {
    return Uint8Array.from(atob(src.slice(src.indexOf(",") + 1)), (char) => char.charCodeAt(0));
  } catch {
    throw new AcquisitionFailure(DEGRADATION_REASON.undecodable);
  }
};

// Rasters are decoded by the Images binding, outside the Worker's memory, and judged on what
// decoding reports rather than on attributes or Content-Type. null is a raster under the size
// floor: an avatar or a tracking pixel, dropped without a degradation.
const toStoredBytes = async (env: Cloudflare.Env, raw: Uint8Array) => {
  if (isSvg(raw)) {
    const markup = await stripScripts(new TextDecoder().decode(raw));

    return { bytes: new TextEncoder().encode(markup), contentType: SVG_CONTENT_TYPE };
  }

  const blob = new Blob([raw]);

  try {
    const { width, height } = (await env.IMAGES.info(blob.stream())) as {
      width?: number;
      height?: number;
    };

    if (width == null || height == null || Math.min(width, height) < MIN_IMAGE_DIMENSION) {
      return null;
    }

    const output = await env.IMAGES.input(blob.stream()).output({
      format: "image/webp",
    });

    return {
      bytes: new Uint8Array(await output.response().arrayBuffer()),
      contentType: output.contentType(),
    };
  } catch {
    throw new AcquisitionFailure(DEGRADATION_REASON.undecodable);
  }
};

const sha256 = async (bytes: Uint8Array) =>
  [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");

export type AcquireRequest = {
  textUnits: (ParagraphUnit | CodeUnit)[];
  declaredImages: DeclaredImage[];
  itemId: string;
  pageUrl: string;
};

// The per-host bound is the one that matters: an article's many same-host images must never open
// that many connections to a server nagara has no relationship with. The global bound covers the
// decode and the store too, so no more than that many images are held in memory at once. It is
// taken inside the host's permit, so an image waiting on a busy host holds no global permit.
export const acquire = async (
  env: Cloudflare.Env,
  { textUnits, declaredImages, itemId, pageUrl }: AcquireRequest,
) => {
  const global = semaphore(env.imageFetchConcurrency);
  const perHost = new Map<string, ReturnType<typeof semaphore>>();

  const hostLimit = (host: string) => {
    let limit = perHost.get(host);

    if (limit == null) {
      limit = semaphore(env.imageFetchPerHost);
      perHost.set(host, limit);
    }

    return limit;
  };

  const store = async (
    { after, alt }: DeclaredImage,
    raw: Uint8Array,
  ): Promise<Acquired | null> => {
    const stored = await toStoredBytes(env, raw);

    if (stored == null) {
      return null;
    }

    const hash = await sha256(stored.bytes);

    await env.BUCKET.put(imageKey(hash), stored.bytes, {
      httpMetadata: { contentType: stored.contentType },
    });

    return {
      after,
      unit: {
        type: "image",
        display: `![${alt}](/items/${itemId}/images/${hash})`,
        spoken: imageSpoken(alt.trim()),
        image: hash,
      },
    };
  };

  // A src is often relative to the page; a degradation records where the image was looked for,
  // and keeps the src as written when it does not resolve at all.
  const resolve = (src: string) => (URL.canParse(src, pageUrl) ? new URL(src, pageUrl).href : src);

  // Async so a src that does not parse as a URL rejects this image's promise and becomes its
  // degradation instead of throwing out of the map.
  const acquireOne = async (image: DeclaredImage) => {
    if (image.src.startsWith("data:")) {
      return global(() => store(image, decodeDataUri(image.src)));
    }

    const url = new URL(image.src, pageUrl);

    return hostLimit(url.host)(() => global(async () => store(image, await download(url.href))));
  };

  const outcomes = await Promise.allSettled(declaredImages.map(acquireOne));
  const degradations: Degradation[] = [];
  const acquired: Acquired[] = [];

  outcomes.forEach((outcome, index) => {
    if (outcome.status === "rejected") {
      const reason =
        outcome.reason instanceof AcquisitionFailure
          ? outcome.reason.reason
          : DEGRADATION_REASON.undecodable;

      degradations.push({ type: "image", reason, url: resolve(declaredImages[index].src) });
    } else if (outcome.value != null) {
      acquired.push(outcome.value);
    }
  });

  const byAnchor = Map.groupBy(acquired, ({ after }) => after);
  const imagesAfter = (anchor: number) => (byAnchor.get(anchor) ?? []).map(({ unit }) => unit);
  const units: Unit[] = [
    ...imagesAfter(-1),
    ...textUnits.flatMap((unit, index) => [unit, ...imagesAfter(index)]),
  ];

  return { units, degradations };
};
