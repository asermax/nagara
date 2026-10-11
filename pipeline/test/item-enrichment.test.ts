import { describe, expect, it } from "vitest";
import codeDescribeRefused from "./cassettes/describe/test_a_400_fails_the_unit_without_retrying.yaml?raw";
import { AVATAR_PNG, CHART_PNG } from "./fixtures/images.ts";
import { articleHtml, CLOSING, INTRO } from "./fixtures/item-article.ts";
import { costsOf, readRow, runItem } from "./helpers/item.ts";
import { scenario } from "./helpers/scenario.ts";
import {
  fabricatedDescribes,
  firecrawlPage,
  fromBase64,
  imageFiles,
  requests,
  useServer,
} from "./helpers/services.ts";

useServer();

describe("the images step", () => {
  it("drops a small avatar silently and a 404 with a degradation at its resolved URL, and the item still reaches ready", async () => {
    const itemId = "itm_00000c11";
    const url = `https://c11.test/${itemId}`;

    await scenario({
      itemId,
      domain: "c11.test",
      firecrawl: [
        firecrawlPage(
          articleHtml({
            figures: [
              { src: "https://img.test/avatar.png", alt: "" },
              { src: "/images/missing.png", alt: "" },
            ],
          }),
          url,
        ),
      ],
      handlers: imageFiles({
        "https://img.test/avatar.png": fromBase64(AVATAR_PNG),
        "https://c11.test/images/missing.png": 404,
      }),
    });

    await runItem(itemId, "complete");

    const row = await readRow(itemId);

    expect(row.status).toBe("ready");
    expect(row.units?.map((unit) => unit.type)).toEqual(["paragraph", "code", "paragraph"]);
    expect(row.degradations).toEqual([
      { type: "image", reason: "404", url: "https://c11.test/images/missing.png" },
    ]);
  });

  it("fails in images when the page's only unit is an image that 404s", async () => {
    const itemId = "itm_00000c12";
    const url = `https://c12.test/${itemId}`;

    await scenario({
      itemId,
      domain: "c12.test",
      cassettes: [],
      firecrawl: [
        firecrawlPage(
          articleHtml({
            paragraphs: false,
            codeBlocks: 0,
            figures: [{ src: "https://img.test/gone.png", alt: "" }],
          }),
          url,
        ),
      ],
      handlers: imageFiles({ "https://img.test/gone.png": 404 }),
    });

    await runItem(itemId, "errored");

    expect(await readRow(itemId)).toMatchObject({
      status: "failed",
      current_step: "images",
      error: "no surviving units",
    });
  });
});

describe("the describe step", () => {
  it("floors a code block whose describe fails and records a cached describe as cached", async () => {
    const itemId = "itm_00000c13";
    const url = `https://c13.test/${itemId}`;

    await scenario({
      itemId,
      domain: "c13.test",
      cassettes: [codeDescribeRefused],
      firecrawl: [
        firecrawlPage(
          articleHtml({ figures: [{ src: "https://img.test/chart.png", alt: "" }] }),
          url,
        ),
      ],
      handlers: [
        ...imageFiles({ "https://img.test/chart.png": fromBase64(CHART_PNG) }),
        fabricatedDescribes({ webp: "A blue rectangle fills the frame." }, { cached: true }),
      ],
    });

    await runItem(itemId, "complete");

    const row = await readRow(itemId);

    expect(row.status).toBe("ready");
    expect(row.units?.map((unit) => unit.spoken)).toEqual([
      INTRO,
      "Code with no description.",
      "Image: A blue rectangle fills the frame.",
      CLOSING,
    ]);
    expect(row.degradations).toEqual([{ type: "code", reason: "describe failed" }]);
    expect(requests.filter((request) => request.includes("google-ai-studio"))).toHaveLength(2);
    expect((await costsOf(itemId)).filter(({ type }) => type === "describer")).toEqual([
      { type: "describer", quantity: 1, cached: 1 },
    ]);
  });

  it("describes the first 25 of 30 code blocks in document order and floors the rest", async () => {
    const itemId = "itm_00000c14";
    const url = `https://c14.test/${itemId}`;

    await scenario({
      itemId,
      domain: "c14.test",
      cassettes: [],
      firecrawl: [firecrawlPage(articleHtml({ codeBlocks: 30 }), url)],
      handlers: [fabricatedDescribes({ code: "A Python function that fetches a URL." })],
    });

    await runItem(itemId, "complete");

    const row = await readRow(itemId);
    const code = (row.units ?? []).filter((unit) => unit.type === "code");

    expect(row.status).toBe("ready");
    expect(code.map((unit) => unit.spoken)).toEqual([
      ...Array.from({ length: 25 }, () => "Code: A Python function that fetches a URL."),
      ...Array.from({ length: 5 }, () => "Code with no description."),
    ]);
    expect(row.degradations).toEqual(
      Array.from({ length: 5 }, () => ({ type: "code", reason: "describe cap reached" })),
    );
    expect((await costsOf(itemId)).filter(({ type }) => type === "describer")).toHaveLength(25);
  });
});
