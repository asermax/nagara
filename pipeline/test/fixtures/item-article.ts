// The title, the paragraph before the code block and the block itself are the ones the recorded
// describe cassettes were made with, so the code describe replays a real Gemini answer.
export const TITLE = "Testing Async Python";

export const INTRO = "The helper below wraps the retry loop around a single request.";

export const CODE = "async def fetch(url):\n    return await client.get(url)";

export const CLOSING = "The closing paragraph ends the article.";

export const GOOD_ALT = "A blue square drawn on a white background";

export type Figure = { src: string; alt: string };

export const articleHtml = ({
  figures = [],
  codeBlocks = 1,
  ornament = false,
  paragraphs = true,
}: {
  figures?: Figure[];
  codeBlocks?: number;
  ornament?: boolean;
  paragraphs?: boolean;
} = {}) => `<html>
  <head><title>${TITLE}</title></head>
  <body>
    <nav><a href="/">home</a></nav>
    <article class="post">
      <h1>${TITLE}</h1>
      ${paragraphs ? `<p>${INTRO}</p>` : ""}
      ${Array.from({ length: codeBlocks }, () => `<pre><code>${CODE}</code></pre>`).join("\n      ")}
      ${ornament ? "<p>❦</p>" : ""}
      ${figures.map(({ src, alt }) => `<figure><img src="${src}" alt="${alt}"></figure>`).join("\n      ")}
      ${paragraphs ? `<p>${CLOSING}</p>` : ""}
    </article>
    <footer>site chrome</footer>
  </body>
</html>`;

export const articleRecipe = `
export const container = "article.post";
export const ignores = [];
export const inventory = [
  { selector: "h1", role: "title" },
  { selector: "p", role: "unit" },
  { selector: "pre", role: "unit" },
  { selector: "figure", role: "wrapper" },
  { selector: "img", role: "unit" },
  { selector: "code", role: "inline" },
];

export function extract($, toMarkdown) {
  const $container = $("article.post");
  const title = $container.find("h1").first().text();
  const units = [];
  $container.children().each((_, el) => {
    if (el.tagName === "h1") return;
    if (el.tagName === "figure") {
      const img = $(el).find("img").get(0);
      units.push({ type: "image", src: $(img).attr("src"), alt: $(img).attr("alt") ?? "", element: img });
      return;
    }
    units.push({ type: el.tagName === "pre" ? "code" : "paragraph", display: toMarkdown(el), element: el });
  });
  return { title, units };
}
`;

// Drops the code block, so its text stays behind and the validator's leftover report fires.
export const failingRecipe = articleRecipe.replace(
  '    if (el.tagName === "h1") return;',
  '    if (el.tagName === "h1") return;\n    if (el.tagName === "pre") return;',
);
