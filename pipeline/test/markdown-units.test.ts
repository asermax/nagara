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
function selectorRecipe(selector: string): string {
  return `
export const container = "article";
export function extract($, toMarkdown) {
  const units = $(${JSON.stringify(selector)}).toArray().map((element) => ({
    type: element.tagName === "pre" ? "code" : "paragraph",
    display: toMarkdown(element),
    element,
  }));
  return { title: ${JSON.stringify(TITLE)}, units };
}
`;
}

async function extractUnits(body: string): Promise<Unit[]> {
  const result = await runRecipe(env, selectorRecipe("article > *"), articleWith(body));
  if (!result.ok) {
    throw new Error(JSON.stringify(result.report));
  }
  return result.units;
}

describe("the markdown a declared element converts to", () => {
  it("headings keep their level, and the extracted title is not a unit", async () => {
    const units = await extractUnits("<h2>Background</h2><p>Text.</p><h4>Detail</h4>");

    expect(units.map((unit) => unit.display)).toEqual(["## Background", "Text.", "#### Detail"]);
  });

  it("a blockquote keeps its quote markers on every line, a quoted blank line between paragraphs", async () => {
    const units = await extractUnits(
      "<blockquote><p>First thought.</p><p>Second thought.</p></blockquote>",
    );

    expect(units).toEqual([
      { type: "paragraph", display: "> First thought.\n> \n> Second thought." },
    ]);
  });

  it("an ordered list keeps its start number and indents a nested bullet list", async () => {
    const units = await extractUnits(
      '<ol start="3"><li>Third<ul><li>Aside</li></ul></li><li>Fourth</li></ol>',
    );

    expect(units).toHaveLength(1);
    expect(units[0].display).toMatch(/^3\.\s+Third\n\s+-\s+Aside\n4\.\s+Fourth$/);
  });

  it("a table with a header row becomes a pipe table", async () => {
    const units = await extractUnits(
      "<table><thead><tr><th>Name</th><th>Role</th></tr></thead><tbody><tr><td>Ada</td><td>Author</td></tr></tbody></table>",
    );

    expect(units).toEqual([
      { type: "paragraph", display: "| Name | Role |\n| --- | --- |\n| Ada | Author |" },
    ]);
  });

  it("a table without a header row becomes a pipe table headed by its first row", async () => {
    const units = await extractUnits(
      "<table><tr><td>Name</td><td>Role</td></tr><tr><td>Ada</td><td>Author</td></tr></table>",
    );

    expect(units).toEqual([
      { type: "paragraph", display: "| Name | Role |\n| --- | --- |\n| Ada | Author |" },
    ]);
  });

  it("a pre with a code child and a bare pre both become fenced code units", async () => {
    const units = await extractUnits("<pre><code>x = 1</code></pre><pre>y = 2</pre>");

    expect(units).toEqual([
      { type: "code", display: "```\nx = 1\n```" },
      { type: "code", display: "```\ny = 2\n```" },
    ]);
  });

  it("struck-through text is doubled tildes and a task list keeps its checkboxes", async () => {
    const units = await extractUnits(
      '<p>Plans <del>abandoned</del> kept.</p><ul><li><input type="checkbox" checked> Done</li><li><input type="checkbox"> Pending</li></ul>',
    );

    expect(units[0].display).toBe("Plans ~~abandoned~~ kept.");
    expect(units[1].display).toMatch(/^-\s+\[x\]\s+Done\n-\s+\[ \]\s+Pending$/);
  });

  it("inline elements with no markdown form keep only their text", async () => {
    const units = await extractUnits(
      "<p>Press <kbd>Ctrl</kbd> to <mark>highlight</mark> the 2<sup>nd</sup> line.</p>",
    );

    expect(units).toEqual([
      { type: "paragraph", display: "Press Ctrl to highlight the 2nd line." },
    ]);
  });

  it("a plain paragraph converts unchanged", async () => {
    const units = await extractUnits("<p>Just <em>one</em> sentence.</p>");

    expect(units).toEqual([{ type: "paragraph", display: "Just _one_ sentence." }]);
  });
});

describe("a declared list holding a code block or an image", () => {
  it("stays one unit with its code blocks fenced inside, and passes the fence check", async () => {
    const units = await extractUnits(`<ol>
  <li>Run this:
    <pre><code>make</code></pre>
  </li>
  <li><pre>solo</pre></li>
  <li>Done</li>
</ol>`);

    expect(units).toHaveLength(1);
    expect(units[0].type).toBe("paragraph");
    expect(units[0].display).toMatch(/^1\.\s+Run this:\n\s*\n\s+```\n\s+make\n\s+```/);
    expect(units[0].display).toMatch(/\n2\.\s+```\n\s+solo\n\s+```\n/);
    expect(units[0].display).toMatch(/\n3\.\s+Done$/);
  });

  it("stays one unit with the image as markdown inside its item", async () => {
    const units = await extractUnits(
      '<ul><li>A diagram <img src="/a.png" alt="The flow"></li><li>After</li></ul>',
    );

    expect(units).toEqual([
      { type: "paragraph", display: "-   A diagram ![The flow](/a.png)\n-   After" },
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
});
