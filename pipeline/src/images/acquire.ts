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

  try {
    const { width, height } = (await env.IMAGES.info(new Blob([raw]).stream())) as {
      width?: number;
      height?: number;
    };

    if (width == null || height == null || Math.min(width, height) < MIN_IMAGE_DIMENSION) {
      return null;
    }

    const output = await env.IMAGES.input(new Blob([raw]).stream()).output({
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
// that many connections to a server nagara has no relationship with.
export const acquire = async (
  env: Cloudflare.Env,
  { textUnits, declaredImages, itemId, pageUrl }: AcquireRequest,
) => {
  const global = semaphore(env.imageFetchConcurrency);
  const perHost = new Map<string, ReturnType<typeof semaphore>>();

  const fetchBytes = (src: string) => {
    if (src.startsWith("data:")) {
      return Promise.resolve(decodeDataUri(src));
    }

    const url = new URL(src, pageUrl);

    if (!perHost.has(url.host)) {
      perHost.set(url.host, semaphore(env.imageFetchPerHost));
    }

    return global(() =>
      (perHost.get(url.host) as ReturnType<typeof semaphore>)(() => download(url.href)),
    );
  };

  const acquireOne = async ({ after, src, alt }: DeclaredImage): Promise<Acquired | null> => {
    const stored = await toStoredBytes(env, await fetchBytes(src));

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

  const outcomes = await Promise.allSettled(declaredImages.map(acquireOne));
  const degradations: Degradation[] = [];
  const byAnchor = new Map<number, ImageUnit[]>();

  outcomes.forEach((outcome, index) => {
    if (outcome.status === "rejected") {
      const reason =
        outcome.reason instanceof AcquisitionFailure
          ? outcome.reason.reason
          : DEGRADATION_REASON.undecodable;

      degradations.push({ type: "image", reason, url: declaredImages[index].src });
    } else if (outcome.value != null) {
      byAnchor.set(outcome.value.after, [
        ...(byAnchor.get(outcome.value.after) ?? []),
        outcome.value.unit,
      ]);
    }
  });

  const units: Unit[] = [
    ...(byAnchor.get(-1) ?? []),
    ...textUnits.flatMap((unit, index) => [unit, ...(byAnchor.get(index) ?? [])]),
  ];

  return { units, degradations };
};
