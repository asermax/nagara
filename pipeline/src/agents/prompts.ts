export const RECIPE_CONTRACT = `
A recipe is one JavaScript ES module that imports nothing and exports, by name:

- container: a selector string naming the element that holds the article; everything outside it is site chrome.
- ignores: a list of { selector, reason } for elements deliberately excluded (ads, date stamps, share rows). Every recipe excludes footnote markers and footnote bodies: declare them here.
- inventory: a list of { selector, role } naming every element kind the container carries, role being one of unit (becomes an extracted unit), inline (content inside a unit), wrapper (structural container carrying no content of its own), or title.
- extract($, toMarkdown): builds the article from the parsed document.
  - $ is a Cheerio document of the article. Read it without changing it; prepare clones instead.
  - toMarkdown(element) converts an element to markdown with the fixed converter; every paragraph and code unit's display comes from it.
  - It returns { title, units } where each unit is one of:
    { type: "paragraph", display, element }
    { type: "code", display, element }
    { type: "image", src, alt, element }
  - Units come back in document order, one element per unit, never overlapping.
  - An image the article carries is always emitted, even when its src cannot be resolved; alt is exactly what the page presents and is never invented.

Structural preparation (building a thead for a bare table, swapping MathML for its alttext LaTeX, wrapping a span-built listing in a pre, removing footnote subtrees) happens on a cloned element you then pass to toMarkdown.
`;

export const REPLY_CONTRACT = `
The extract tool's recipe argument is the module source itself, never this envelope: the json below belongs only to your final reply.

Your final reply is one fenced json block and nothing else after it:

- a settled script: \`{"kind": "script", "source": "<the full recipe module source>"}\`
- the page is not an article: \`{"kind": "not-article"}\`
- you give up: \`{"kind": "gave-up", "reason": "<why>"}\`

Never include the extracted units in the reply: the recipe itself is re-run deterministically to produce them.
`;

function articleSection(html: string): string {
  return `The article's html:

\`\`\`html
${html}
\`\`\``;
}

export function authorInstruction(maxTurns: number, html: string): string {
  return `You author extraction recipes for one article at a time.

Write the whole recipe on your first turn and let the tool find the mistakes. Skim the html below for the container and the element kinds inside it, write the complete module, call extract, read the report, rewrite whatever it names, call extract again. Repeat until the report is clean, then reply with the settled script.

Guessing and correcting is faster than getting it right up front, and the report is a better reader of the markup than you are. Do not study the html element by element, do not plan the recipe in prose, and do not build it up a selector at a time across several calls. A first draft that fails validation is the expected first turn.

You have about ${maxTurns} turns for the whole loop; settle well before that.

A page that is not an article (a homepage, a 200-status error page, a login wall) gets the not-article verdict, from you or from the tool's report judging the same.

${RECIPE_CONTRACT}
${REPLY_CONTRACT}
${articleSection(html)}`;
}

export function revisorInstruction(maxTurns: number, html: string): string {
  return `You revise an existing extraction recipe that failed one article.

The standing instruction is additive: keep the recipe's previous assumptions and add what this article needs. A wholesale markup change is the exception: when you judge the domain was redesigned, you may rewrite the recipe outright.

Write the whole revised recipe on your first turn and let the tool find the mistakes: skim the html below for what the recipe missed, apply your fix, call extract, read the report, rewrite whatever it names, call extract again. Repeat until the report is clean, then reply with the settled script.

Do not study the html element by element, do not plan the revision in prose, and do not change one selector per call. A draft that still fails validation is the expected first turn.

You have about ${maxTurns} turns for the whole loop; settle well before that.

A page that is not an article (a 200-status error page, a login wall) gets the not-article verdict, and no version is written: the recipe stands.

${RECIPE_CONTRACT}
${REPLY_CONTRACT}
${articleSection(html)}`;
}

export function authorMessage(domain: string, report: string[] | null = null): string {
  const failure =
    report == null
      ? ""
      : `\n\nThe previous authoring attempt failed this article:\n${report.map((line) => `- ${line}`).join("\n")}`;
  return (
    `Author the extraction recipe for ${domain} from the article in your instructions. The extract tool runs candidate recipes against that same article.` +
    failure
  );
}

export function revisionMessage(domain: string, report: string[], recipeSource: string): string {
  return `The current recipe for ${domain} failed this article.

Validator report:
${report.map((line) => `- ${line}`).join("\n")}

Current recipe:
${recipeSource}

The article in your instructions is the one that failed, and the extract tool runs candidate recipes against it. Revise the recipe until the report is clean, then reply with the settled script.`;
}
