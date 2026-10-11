import { imageKey, type Unit } from "@nagara/common";
import { SVG_CONTENT_TYPE } from "../images/svg.ts";
import { describe } from "./core.ts";
import { altOf, type DescribeJob } from "./jobs.ts";
import { codePrompt, imagePrompt } from "./prompts.ts";

const FENCE_LINE = /^\s*(```|~~~)/;

// The describer reads the block's interior, without its fences.
const codeOf = (display: string) => {
  const lines = display.split("\n");

  return lines.length >= 2 && FENCE_LINE.test(lines[0]) ? lines.slice(1, -1).join("\n") : display;
};

const toBase64 = (bytes: Uint8Array) => {
  let binary = "";

  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }

  return btoa(binary);
};

// An SVG goes as its markup in a text/plain part: the model reads the text the markup carries,
// such as a formula's LaTeX in a <title>, which a rasterised copy only lets it read symbol by symbol.
const imagePart = async (env: Cloudflare.Env, hash: string) => {
  const object = await env.BUCKET.get(imageKey(hash));

  if (object == null) {
    throw new Error(`the stored image ${hash} is missing`);
  }

  return {
    inlineData: {
      mimeType: object.httpMetadata?.contentType === SVG_CONTENT_TYPE ? "text/plain" : "image/webp",
      data: toBase64(new Uint8Array(await object.arrayBuffer())),
    },
  };
};

export const describeOne = async (
  env: Cloudflare.Env,
  units: Unit[],
  title: string | null,
  { index, kind }: DescribeJob,
) => {
  const unit = units[index];

  if (kind === "code") {
    return describe(env, [
      { text: codePrompt(title, index > 0 ? units[index - 1].spoken : null, codeOf(unit.display)) },
    ]);
  }

  if (unit.type !== "image") {
    throw new Error(`unit ${index} is not an image`);
  }

  return describe(env, [
    { text: imagePrompt(title, altOf(unit.display).trim()) },
    await imagePart(env, unit.image),
  ]);
};
