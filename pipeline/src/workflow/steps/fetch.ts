import { NonRetryableError } from "cloudflare:workflows";
import { database, recordFetch, STEP } from "@nagara/common";
import { scrape } from "../../firecrawl/client.ts";
import { domainFromUrl } from "../../recipes/store.ts";
import { requireItem } from "../require-item.ts";
import { runStep, type StepContext } from "../wrapper.ts";

// The HTML rides as this step's result, which a step caps near 1 MiB. The cap is checked against
// the result as it is serialized, escaping included, so a page that would not fit fails here with
// its own error instead of failing the Workflow when the result is stored.
export const fetchStep = (ctx: StepContext) =>
  runStep(ctx, STEP.fetch, "queued", "2 minutes", async () => {
    const { env, itemId, instanceId } = ctx;
    const db = database(env.DB);
    const item = await requireItem(db, itemId);
    const page = await scrape(env.FIRECRAWL_API_KEY, item.url);
    const domain = domainFromUrl(page.finalUrl);

    // The credit is spent the moment the scrape returns, so it is recorded even when the page
    // turns out to be empty.
    await recordFetch(
      db,
      itemId,
      { workflow_instance_id: instanceId, extraction_domain: domain },
      {
        type: "firecrawl",
        quantity: page.creditsUsed,
        unit: "credits",
        dollars: page.creditsUsed * env.firecrawlDollarsPerCredit,
        detail: { destination: page.finalUrl, proxy: page.proxy },
      },
    );

    if (page.html == null) {
      throw new Error("firecrawl returned no HTML");
    }

    const result = { html: page.html, domain };
    const size = new TextEncoder().encode(JSON.stringify(result)).byteLength;

    if (size > env.maxHtmlBytes) {
      throw new NonRetryableError(
        `the fetched page serializes to ${size} bytes, over the ${env.maxHtmlBytes}-byte cap`,
      );
    }

    return result;
  });
