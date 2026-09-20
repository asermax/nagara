export const RECIPE_CONTRACT = `
A recipe is one JavaScript ES module that imports nothing and exports:

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
Your final reply is one fenced json block and nothing else after it:

- a settled script: \`{"kind": "script", "source": "<the full recipe module source>"}\`
- the page is not an article: \`{"kind": "not-article"}\`
- you give up: \`{"kind": "gave-up", "reason": "<why>"}\`

Never include the extracted units in the reply: the recipe itself is re-run deterministically to produce them.
`;

export function authorInstruction(maxTurns: number): string {
  return `You author extraction recipes for one article at a time.

Work with the extract tool: draft the recipe, run it against the article, read its report, and fix what the report names. Repeat until the report is clean, then reply with the settled script.

You have about ${maxTurns} turns for the whole loop; settle well before that.

A page that is not an article (a homepage, a 200-status error page, a login wall) gets the not-article verdict, from you or from the tool's report judging the same.

${RECIPE_CONTRACT}
${REPLY_CONTRACT}`;
}

export function revisorInstruction(maxTurns: number): string {
  return `You revise an existing extraction recipe that failed one article.

The standing instruction is additive: keep the recipe's previous assumptions and add what this article needs. A wholesale markup change is the exception: when you judge the domain was redesigned, you may rewrite the recipe outright.

Work with the extract tool: adjust the recipe, run it against the article, read its report, fix what it names. Repeat until the report is clean, then reply with the settled script.

You have about ${maxTurns} turns for the whole loop; settle well before that.

A page that is not an article (a 200-status error page, a login wall) gets the not-article verdict, and no version is written: the recipe stands.

${RECIPE_CONTRACT}
${REPLY_CONTRACT}`;
}

export function authorMessage(domain: string, report: string[] | null = null): string {
  const failure =
    report == null
      ? ""
      : `\n\nThe previous authoring attempt failed this article:\n${report.map((line) => `- ${line}`).join("\n")}`;
  return (
    `Author the extraction recipe for ${domain} from the article this conversation was opened with. The extract tool runs candidate recipes against that article; you do not need the html in this message.` +
    failure
  );
}

export function revisionMessage(domain: string, report: string[], recipeSource: string): string {
  return `The current recipe for ${domain} failed this article.

Validator report:
${report.map((line) => `- ${line}`).join("\n")}

Current recipe:
${recipeSource}

The article this conversation was opened with is the one that failed, and the extract tool runs candidate recipes against it; you do not need the html in this message. Revise the recipe until the report is clean, then reply with the settled script.`;
}
