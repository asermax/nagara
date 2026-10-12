const SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape";

type ScrapeResponse = {
  success: boolean;
  data?: {
    rawHtml?: string;
    metadata?: {
      url?: string;
      sourceURL?: string;
      creditsUsed?: number;
      proxyUsed?: string;
    };
  };
};

export type Scrape = {
  html: string | null;
  finalUrl: string;
  creditsUsed: number;
  proxy: string | null;
};

// Firecrawl's SDK fails in workerd before it sends anything, so this is a plain fetch that sets the
// scrape options explicitly rather than relying on Firecrawl's defaults. rawHtml keeps the images
// firecrawl's cleaned HTML drops; markdown costs no extra credit and is evidence nothing reads.
// What a scrape bills is the response's creditsUsed.
export const scrape = async (apiKey: string, url: string): Promise<Scrape> => {
  const response = await fetch(SCRAPE_URL, {
    method: "POST",
    headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
    body: JSON.stringify({
      url,
      onlyMainContent: true,
      skipTlsVerification: true,
      removeBase64Images: true,
      fastMode: false,
      blockAds: true,
      storeInCache: true,
      maxAge: 14400000,
      formats: ["rawHtml", "markdown"],
      proxy: "auto",
      mobile: false,
    }),
  });

  if (!response.ok) {
    throw new Error(`firecrawl answered ${response.status}`);
  }

  const { data } = (await response.json()) as ScrapeResponse;

  return {
    html: data?.rawHtml || null,
    finalUrl: data?.metadata?.url ?? url,
    creditsUsed: data?.metadata?.creditsUsed ?? 0,
    proxy: data?.metadata?.proxyUsed ?? null,
  };
};
