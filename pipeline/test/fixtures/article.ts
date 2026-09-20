export const articleHtml = `
<html>
  <head><title>Colorless Green Ideas</title></head>
  <body>
    <nav><a href="/">home</a></nav>
    <article class="post">
      <h1>Colorless Green Ideas</h1>
      <p class="lede">Noam <em>Chomsky</em> coined the sentence to show that syntax can outrun sense.</p>
      <pre><code>const ideas = colorless();</code></pre>
      <figure><img src="/img/ideas.png" alt="A green idea, colorless"><figcaption>The famous sentence.</figcaption></figure>
      <p>Second paragraph with a <a href="https://example.com">link</a>.</p>
      <div class="ad">Buy nothing!</div>
    </article>
    <footer>site chrome</footer>
  </body>
</html>
`;

export const passingRecipe = `
export const container = "article.post";
export const ignores = [{ selector: "div.ad", reason: "advertisement" }];
export const inventory = [
  { selector: "h1", role: "title" },
  { selector: "p", role: "unit" },
  { selector: "pre", role: "unit" },
  { selector: "figure", role: "unit" },
  { selector: "figcaption", role: "unit" },
  { selector: "em", role: "inline" },
  { selector: "a", role: "inline" },
  { selector: "code", role: "inline" },
];

export function extract($, toMarkdown) {
  const $container = $("article.post");
  const title = $container.find("h1").first().text();
  const units = [];
  $container.children().each((_, el) => {
    const $el = $(el);
    if (el.tagName === "h1") return;
    if (el.tagName === "div") return;
    if (el.tagName === "figure") {
      const img = $el.find("img").first();
      units.push({ type: "image", src: img.attr("src"), alt: img.attr("alt") ?? "", element: img.get(0) });
      const caption = $el.find("figcaption").first();
      if (caption.length > 0) {
        units.push({ type: "paragraph", display: toMarkdown(caption.get(0)), element: caption.get(0) });
      }
      return;
    }
    units.push({
      type: el.tagName === "pre" ? "code" : "paragraph",
      display: toMarkdown(el),
      element: el,
    });
  });
  return { title, units };
}
`;

export const failingRecipe = `
export const container = "article.post";
export const ignores = [{ selector: "div.ad", reason: "advertisement" }];
export const inventory = [
  { selector: "h1", role: "title" },
  { selector: "p", role: "unit" },
  { selector: "pre", role: "unit" },
  { selector: "figure", role: "unit" },
  { selector: "figcaption", role: "unit" },
  { selector: "em", role: "inline" },
  { selector: "a", role: "inline" },
  { selector: "code", role: "inline" },
];

export function extract($, toMarkdown) {
  const $container = $("article.post");
  const title = $container.find("h1").first().text();
  const units = [];
  $container.children().each((_, el) => {
    const $el = $(el);
    if (el.tagName === "h1") return;
    if (el.tagName === "figure") return;
    if (el.tagName === "pre") return;
    if (el.tagName === "div") return;
    units.push({ type: "paragraph", display: toMarkdown(el), element: el });
  });
  return { title, units };
}
`;
