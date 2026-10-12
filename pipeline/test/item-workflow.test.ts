import { env } from "cloudflare:workers";
import { imageKey } from "@nagara/common";
import { describe, expect, it } from "vitest";
import { CHART_PNG, SQUARE_PNG } from "./fixtures/images.ts";
import { articleHtml, CLOSING, GOOD_ALT, INTRO } from "./fixtures/item-article.ts";
import { costsOf, readRow, runItem } from "./helpers/item.ts";
import { logStatuses, scenario, statusesOf } from "./helpers/scenario.ts";
import {
  fabricatedDescribes,
  firecrawlPage,
  fromBase64,
  imageFiles,
  requests,
  useServer,
} from "./helpers/services.ts";

useServer();

const SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="60" onload="alert(1)"><script>alert(1)</script><rect width="120" height="60" fill="blue"/></svg>';

const firecrawlCalls = () => requests.filter((request) => request.includes("api.firecrawl.dev"));

const distinct = (statuses: string[]) =>
  statuses.filter((status, index) => status !== statuses[index - 1]);

describe("an item run", () => {
  it("carries an article with code, rasters, an SVG and a repeated image to ready", async () => {
    await logStatuses();

    const itemId = "itm_000000c1";
    const { synthesis, recipeVersionId } = await scenario({
      itemId,
      domain: "c1.test",
      firecrawl: [
        firecrawlPage(
          articleHtml({
            ornament: true,
            figures: [
              { src: "https://img.test/chart.png", alt: "" },
              { src: "https://img.test/diagram.svg", alt: "" },
              { src: "https://img.test/square.png", alt: GOOD_ALT },
              { src: "https://img.test/chart.png", alt: "" },
            ],
          }),
          "https://www.c1.test/itm_000000c1",
        ),
      ],
      handlers: [
        ...imageFiles({
          "https://img.test/chart.png": fromBase64(CHART_PNG),
          "https://img.test/square.png": fromBase64(SQUARE_PNG),
          "https://img.test/diagram.svg": SVG,
        }),
        fabricatedDescribes({
          webp: "A blue rectangle fills the frame.",
          svg: "A blue **rectangle** drawn as a diagram.",
        }),
      ],
    });

    await runItem(itemId, "complete");

    const row = await readRow(itemId);
    const [chart, svg, square, repeated] = (row.units ?? []).filter(
      (unit) => unit.type === "image",
    );

    expect(row).toMatchObject({
      status: "ready",
      title: "Testing Async Python",
      current_step: null,
      error: null,
      extraction_domain: "c1.test",
      workflow_instance_id: "wf-itm_000000c1",
      recipe_version_id: recipeVersionId,
      audio_format: "audio/ogg",
      duration: 7,
      degradations: null,
    });
    expect(row.units?.map((unit) => [unit.type, unit.spoken, unit.start, unit.end])).toEqual([
      ["paragraph", INTRO, 0, 1],
      [
        "code",
        "Code: An asynchronous Python helper function wraps the retry loop around a single request.",
        1,
        2,
      ],
      ["image", "Image: A blue rectangle fills the frame.", 2, 3],
      ["image", "Image: A blue rectangle drawn as a diagram.", 3, 4],
      ["image", `Image: ${GOOD_ALT}`, 4, 5],
      ["image", "Image: A blue rectangle fills the frame.", 5, 6],
      ["paragraph", CLOSING, 6, 7],
    ]);
    expect(chart).toMatchObject({ display: `![](/items/${itemId}/images/${chart.image})` });
    expect(square.display).toBe(`![${GOOD_ALT}](/items/${itemId}/images/${square.image})`);
    expect(repeated.image).toBe(chart.image);
    expect(new Set([chart.image, svg.image, square.image]).size).toBe(3);

    const storedChart = await env.BUCKET.get(imageKey(chart.image));
    const storedSvg = await env.BUCKET.get(imageKey(svg.image));

    expect(storedChart?.httpMetadata?.contentType).toBe("image/webp");
    expect(storedSvg?.httpMetadata?.contentType).toBe("image/svg+xml");

    const markup = (await storedSvg?.text()) ?? "";

    expect(markup).toContain("<rect");
    expect(markup).not.toContain("<script");
    expect(markup).not.toContain("onload");

    expect((await costsOf(itemId)).map(({ type }) => type).sort()).toEqual([
      "describer",
      "describer",
      "describer",
      "describer",
      "firecrawl",
      "tts",
    ]);

    const [start] = synthesis.calls.starts;
    const destination = new URL(start.destination);

    expect(start.paragraphs).toEqual(row.units?.map((unit) => unit.spoken));
    expect(start.voice).toBe("af_heart");
    expect(start.headers.get("Modal-Key")).toBe("test-modal-key");
    expect(start.headers.get("Modal-Secret")).toBe("test-modal-secret");
    expect(destination.host).toBe("tunnel.test");
    expect(destination.pathname).toBe(`/s3/nagara/audio/${itemId}`);
    expect(destination.searchParams.get("X-Amz-Expires")).toBe("3600");

    expect(distinct(await statusesOf(itemId))).toEqual([
      "queued fetch",
      "queued lease",
      "generating recipe",
      "generating release",
      "generating images",
      "generating describe",
      "generating start synthesis",
      "generating wait for synthesis",
      "generating store",
      "ready",
    ]);
  });

  it("retries a Firecrawl 503 inside the fetch step without ever showing failed", async () => {
    await logStatuses();

    const itemId = "itm_000000c2";
    const url = "https://c2.test/itm_000000c2";

    await scenario({
      itemId,
      domain: "c2.test",
      firecrawl: [{ status: 503, body: { success: false } }, firecrawlPage(articleHtml(), url)],
    });

    await runItem(itemId, "complete");

    expect((await readRow(itemId)).status).toBe("ready");
    expect(firecrawlCalls()).toHaveLength(2);
    expect(await statusesOf(itemId)).not.toContainEqual(expect.stringMatching(/^failed/));
  });

  it("fails at once in fetch a page whose serialized result is over the cap, though its HTML is not", async () => {
    const itemId = "itm_000000c3";
    const url = "https://c3.test/itm_000000c3";
    const html = articleHtml().replace("</body>", `<p>${'"'.repeat(600_000)}</p></body>`);

    expect(new TextEncoder().encode(html).byteLength).toBeLessThan(env.maxHtmlBytes);

    await scenario({ itemId, domain: "c3.test", firecrawl: [firecrawlPage(html, url)] });
    await runItem(itemId, "errored");

    expect(await readRow(itemId)).toMatchObject({
      status: "failed",
      current_step: "fetch",
      error: expect.stringMatching(
        /^the fetched page serializes to \d+ bytes, over the 1048576-byte cap$/,
      ),
    });
    expect(firecrawlCalls()).toHaveLength(1);
    expect((await costsOf(itemId)).map(({ type }) => type)).toEqual(["firecrawl"]);
  });

  it("fails with fetch's own error once Firecrawl answers 503 on every attempt", async () => {
    const itemId = "itm_000000c4";
    const unavailable = { status: 503, body: { success: false } };

    await scenario({
      itemId,
      domain: "c4.test",
      firecrawl: [unavailable, unavailable, unavailable],
    });

    const instance = await runItem(itemId, "errored");

    expect(await readRow(itemId)).toMatchObject({
      status: "failed",
      current_step: "fetch",
      error: "firecrawl answered 503",
    });
    expect(firecrawlCalls()).toHaveLength(3);
    await expect(instance.getError()).resolves.toMatchObject({
      message: expect.stringMatching(/503/),
    });
  });
});
