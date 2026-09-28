import { env } from "cloudflare:workers";
import { describe, expect, it } from "vitest";
import { runRecipe } from "../src/runtime/run.ts";
import type { Unit } from "../src/runtime/units.ts";

const TITLE = "A Synthetic Article";

function articleWith(body: string): string {
  return `<html><body><article>${body}</article></body></html>`;
}

// Declares every element the selector matches as one unit, a <pre> as code
// and anything else as a paragraph.
function selectorRecipe(selector: string, title = TITLE): string {
  return `
export const container = "article";
export function extract($, toMarkdown) {
  const units = $(${JSON.stringify(selector)}).toArray().map((element) => ({
    type: element.tagName === "pre" ? "code" : "paragraph",
    display: toMarkdown(element),
    element,
  }));
  return { title: ${JSON.stringify(title)}, units };
}
`;
}

async function extractUnits(body: string, title = TITLE): Promise<Unit[]> {
  const result = await runRecipe(env, selectorRecipe("article > *", title), articleWith(body));
  if (!result.ok) {
    throw new Error(JSON.stringify(result.report));
  }
  return result.units;
}

async function bodyUnits(body: string): Promise<Unit[]> {
  const [title, ...units] = await extractUnits(body);
  expect(title).toEqual({ type: "paragraph", display: `# ${TITLE}` });
  return units;
}

describe("the markdown a declared element converts to", () => {
  it("headings keep their level, after a title unit carrying the extracted title", async () => {
    const units = await extractUnits("<h2>Background</h2><p>Text.</p><h4>Detail</h4>");

    expect(units.map((unit) => unit.display)).toEqual([
      `# ${TITLE}`,
      "## Background",
      "Text.",
      "#### Detail",
    ]);
  });

  it("a blockquote keeps its quote markers on every line, a quoted blank line between paragraphs", async () => {
    const units = await bodyUnits(
      "<blockquote><p>First thought.</p><p>Second thought.</p></blockquote>",
    );

    expect(units).toEqual([
      { type: "paragraph", display: "> First thought.\n> \n> Second thought." },
    ]);
  });

  it("an ordered list keeps its start number and indents a nested bullet list", async () => {
    const units = await bodyUnits(
      '<ol start="3"><li>Third<ul><li>Aside</li></ul></li><li>Fourth</li></ol>',
    );

    expect(units).toHaveLength(1);
    expect(units[0].display).toMatch(/^3\.\s+Third\n\s+-\s+Aside\n4\.\s+Fourth$/);
  });

  it("a table with a header row becomes a pipe table, and an empty title adds no title unit", async () => {
    const units = await extractUnits(
      "<table><thead><tr><th>Name</th><th>Role</th></tr></thead><tbody><tr><td>Ada</td><td>Author</td></tr></tbody></table>",
      "",
    );

    expect(units).toEqual([
      { type: "paragraph", display: "| Name | Role |\n| --- | --- |\n| Ada | Author |" },
    ]);
  });

  it("a table without a header row becomes a pipe table headed by its first row", async () => {
    const units = await bodyUnits(
      "<table><tr><td>Name</td><td>Role</td></tr><tr><td>Ada</td><td>Author</td></tr></table>",
    );

    expect(units).toEqual([
      { type: "paragraph", display: "| Name | Role |\n| --- | --- |\n| Ada | Author |" },
    ]);
  });

  it("a pre with a code child and a bare pre both become fenced code units", async () => {
    const units = await bodyUnits("<pre><code>x = 1</code></pre><pre>y = 2</pre>");

    expect(units).toEqual([
      { type: "code", display: "```\nx = 1\n```" },
      { type: "code", display: "```\ny = 2\n```" },
    ]);
  });

  it("struck-through text is doubled tildes and a task list keeps its checkboxes", async () => {
    const units = await bodyUnits(
      '<p>Plans <del>abandoned</del> kept.</p><ul><li><input type="checkbox" checked> Done</li><li><input type="checkbox"> Pending</li></ul>',
    );

    expect(units[0].display).toBe("Plans ~~abandoned~~ kept.");
    expect(units[1].display).toMatch(/^-\s+\[x\]\s+Done\n-\s+\[ \]\s+Pending$/);
  });

  it("inline elements with no markdown form keep only their text", async () => {
    const units = await bodyUnits(
      "<p>Press <kbd>Ctrl</kbd> to <mark>highlight</mark> the 2<sup>nd</sup> line.</p>",
    );

    expect(units).toEqual([
      { type: "paragraph", display: "Press Ctrl to highlight the 2nd line." },
    ]);
  });

  it("a plain paragraph converts unchanged", async () => {
    const units = await bodyUnits("<p>Just <em>one</em> sentence.</p>");

    expect(units).toEqual([{ type: "paragraph", display: "Just _one_ sentence." }]);
  });
});

describe("a declared list holding a code block or an image", () => {
  it("splits around a code block in a top-level item, the part after continuing the numbering", async () => {
    const units = await bodyUnits(`<ol start="4">
  <li>Install</li>
  <li>Run this:
    <pre><code>make</code></pre>
  </li>
  <li>Done</li>
</ol>`);

    expect(units).toEqual([
      { type: "paragraph", display: "4.  Install\n5.  Run this:" },
      { type: "code", display: "```\nmake\n```" },
      { type: "paragraph", display: "6.  Done" },
    ]);
  });

  it("resumes a code block three levels deep with an empty item at each enclosing level", async () => {
    const units = await bodyUnits(`<ol>
  <li>Item A</li>
  <li>Item B
    <ol>
      <li>Item B.1</li>
      <li>Item B.2
        <ul>
          <li>Deep one</li>
          <li>Deep two:
            <pre>x = 1</pre>
          </li>
          <li>Deep three</li>
        </ul>
      </li>
      <li>Item B.3</li>
    </ol>
  </li>
  <li>Item C</li>
</ol>`);

    expect(units).toEqual([
      {
        type: "paragraph",
        display:
          "1.  Item A\n2.  Item B\n    1.  Item B.1\n    2.  Item B.2\n        -   Deep one\n        -   Deep two:",
      },
      { type: "code", display: "```\nx = 1\n```" },
      {
        type: "paragraph",
        display: "2.  2.  -   Deep three\n    3.  Item B.3\n3.  Item C",
      },
    ]);
  });

  it("surfaces an img, a figure, a picture and an svg in a nested list as image units carrying the element's src and alt", async () => {
    const units = await bodyUnits(`<ul>
  <li>Outer
    <ul>
      <li>An img <img src="/a.png" alt="A"></li>
      <li><figure><img src="/b.png" alt="B"></figure></li>
      <li><picture><source srcset="/c.webp"><img src="/c.png" alt="C"></picture> after</li>
      <li>Svg <svg viewBox="0 0 1 1"><rect width="1" height="1"></rect></svg></li>
    </ul>
  </li>
</ul>`);

    expect(units).toEqual([
      { type: "paragraph", display: "-   Outer\n    -   An img" },
      { type: "image", display: "A", src: "/a.png", alt: "A" },
      { type: "image", display: "B", src: "/b.png", alt: "B" },
      { type: "image", display: "C", src: "/c.png", alt: "C" },
      { type: "paragraph", display: "-   -   after\n    -   Svg" },
      { type: "image", display: "", src: "", alt: "" },
    ]);
  });

  it("splits around two code blocks into five units, continuing the numbering twice", async () => {
    const units = await bodyUnits(`<ol>
  <li>One <pre>a</pre></li>
  <li>Two</li>
  <li>Three <pre>b</pre></li>
  <li>Four</li>
</ol>`);

    expect(units).toEqual([
      { type: "paragraph", display: "1.  One" },
      { type: "code", display: "```\na\n```" },
      { type: "paragraph", display: "2.  Two\n3.  Three" },
      { type: "code", display: "```\nb\n```" },
      { type: "paragraph", display: "4.  Four" },
    ]);
  });

  it("does not repeat an item whose only content is the code block", async () => {
    const units = await bodyUnits(`<ul>
  <li>Before</li>
  <li><pre>solo</pre></li>
  <li>After</li>
</ul>`);

    expect(units).toEqual([
      { type: "paragraph", display: "-   Before" },
      { type: "code", display: "```\nsolo\n```" },
      { type: "paragraph", display: "-   After" },
    ]);
  });

  it("opens the part after with the text that followed the code block in the same item", async () => {
    const units = await bodyUnits(`<ol>
  <li>Lead <pre>z</pre> trailing words</li>
  <li>Next</li>
</ol>`);

    expect(units).toEqual([
      { type: "paragraph", display: "1.  Lead" },
      { type: "code", display: "```\nz\n```" },
      { type: "paragraph", display: "1.  trailing words\n2.  Next" },
    ]);
  });
});

describe("a declared unit that is a list item on its own", () => {
  it("is reported with its position and path, its list and the whole-list rule, and returns no units", async () => {
    const result = await runRecipe(
      env,
      selectorRecipe("article li"),
      articleWith('<ol class="steps"><li>First</li><li>Second</li></ol>'),
    );

    expect(result).toEqual({
      ok: false,
      report: [
        'unit 0 at html > body:nth-child(1) > article:nth-child(1) > ol:nth-child(1) > li:nth-child(1) is an <li> on its own, one item of the <ol class="steps"> at html > body:nth-child(1) > article:nth-child(1) > ol:nth-child(1); a recipe hands a list over whole: declare the whole list as one unit',
        'unit 1 at html > body:nth-child(1) > article:nth-child(1) > ol:nth-child(1) > li:nth-child(2) is an <li> on its own, one item of the <ol class="steps"> at html > body:nth-child(1) > article:nth-child(1) > ol:nth-child(1); a recipe hands a list over whole: declare the whole list as one unit',
      ],
    });
  });

  it("is reported alongside the leftover text in one report", async () => {
    const result = await runRecipe(
      env,
      selectorRecipe("article li:first-child"),
      articleWith("<ul><li>Kept</li><li>Forgotten</li></ul>"),
    );

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.report).toHaveLength(2);
      expect(result.report[0]).toMatch(/^unit 0 at .* is an <li> on its own, one item of the <ul>/);
      expect(result.report[1]).toMatch(/^readable text is left .*Forgotten/);
    }
  });

  it("fails the run with the report alone, discarding the split of another list", async () => {
    const result = await runRecipe(
      env,
      selectorRecipe("article > ol, article > ul > li"),
      articleWith("<ol><li>Run <pre>make</pre></li><li>Done</li></ol><ul><li>Loose</li></ul>"),
    );

    expect(result.ok).toBe(false);
    expect("units" in result).toBe(false);
    if (!result.ok) {
      expect(result.report).toHaveLength(1);
      expect(result.report[0]).toMatch(/^unit 1 at .* is an <li> on its own, one item of the <ul>/);
    }
  });
});
