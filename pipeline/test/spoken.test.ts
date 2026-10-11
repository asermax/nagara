import { describe, expect, it } from "vitest";
import { isCruft } from "../src/images/alt.ts";
import { toSpoken } from "../src/spoken/derive.ts";
import { sanitizeSpoken } from "../src/spoken/sanitize.ts";
import { isUnspeakable } from "../src/spoken/typed-units.ts";

describe("the spoken form", () => {
  it("equals the display for plain text", () => {
    expect(toSpoken("Para one.")).toBe("Para one.");
  });

  it("reads soft wraps as one line", () => {
    expect(toSpoken("A wrapped\nparagraph here.")).toBe("A wrapped paragraph here.");
  });

  it("keeps an ordered item's number from the list start", () => {
    expect(toSpoken("3. Write the interface\n4. Implement it")).toBe(
      "3. Write the interface\n4. Implement it",
    );
  });

  it.each([
    ["# The Title", "The Title"],
    ["## A Section", "A Section"],
  ])("reads the heading %j as its words", (unit, expected) => {
    expect(toSpoken(unit)).toBe(expected);
  });

  it("reads each quoted paragraph on its own line without its marker", () => {
    expect(toSpoken("> First quoted.\n>\n> Second quoted.")).toBe("First quoted.\nSecond quoted.");
  });

  it("never fuses two paragraphs of one unit", () => {
    expect(toSpoken("First paragraph\n\nSecond paragraph")).toBe(
      "First paragraph\nSecond paragraph",
    );
  });

  it("reads each unordered item on its own line with no full stop added", () => {
    expect(toSpoken("- First item\n- Second item\n- Third item")).toBe(
      "First item\nSecond item\nThird item",
    );
  });

  it("reads nested lists in document order with their own numbering", () => {
    expect(
      toSpoken("1. Outer one\n   - Middle\n     1. Inner one\n     2. Inner two\n2. Outer two"),
    ).toBe("1. Outer one\nMiddle\n1. Inner one\n2. Inner two\n2. Outer two");
  });

  it("gives an item opening with a nested list no line of its own", () => {
    expect(toSpoken("2.  3.  Inner item\n3. Outer item")).toBe("3. Inner item\n3. Outer item");
  });

  it("gives an ordered item holding only an image or a code block no line", () => {
    expect(
      toSpoken(
        "1. First\n2. ![A chart](https://example.test/chart.png)\n3. ```sh\n   npm install tool\n   ```\n4. Last",
      ),
    ).toBe("1. First\n4. Last");
  });

  it("keeps a code block or image inside a list item silent while the item's text reads", () => {
    expect(
      toSpoken(
        "- Install it:\n\n  ```sh\n  npm install tool\n  ```\n" +
          "- See the chart ![A chart of requests](https://example.test/chart.png)\n" +
          "- Done",
      ),
    ).toBe("Install it:\nSee the chart\nDone");
  });

  it("keeps a task checkbox silent whether checked or not", () => {
    expect(toSpoken("- [x] a\n- [ ] b")).toBe("a\nb");
  });

  it("reads struck-through text as its words", () => {
    expect(toSpoken("~~rejection~~ redirection")).toBe("rejection redirection");
  });

  it("reduces a link to its anchor text", () => {
    expect(toSpoken("See [the docs](https://example.test/x).")).toBe("See the docs.");
  });

  it("reads emphasis as its inner text", () => {
    expect(toSpoken("Deep **sessions** where *they* run.")).toBe("Deep sessions where they run.");
  });

  it("clears the literal markers of run-in bold the parser leaves", () => {
    expect(toSpoken("**Issue and PR review.**Agents help.")).toBe(
      "Issue and PR review. Agents help.",
    );
  });

  it("speaks a code block as the placeholder", () => {
    expect(toSpoken("```python\ndef f():\n    return 1\n\n\ndef g():\n    return 2\n```")).toBe(
      "Code sample.",
    );
  });

  it("reads a table as one header-aware line per body row", () => {
    expect(
      toSpoken("| Feature | Status |\n| --- | --- |\n| Extraction | done |\n| Timing | exact |"),
    ).toBe("Feature: Extraction, Status: done.\nFeature: Timing, Status: exact.");
  });

  it("reads the header cells of a table with no body rows", () => {
    expect(toSpoken("| Feature | Status |\n| --- | --- |")).toBe("Feature, Status.");
  });

  it("reads a table cell's code span without its backticks", () => {
    expect(toSpoken("| Name | Type |\n| --- | --- |\n| count | `int` |\n| ratio | `float` |")).toBe(
      "Name: count, Type: int.\nName: ratio, Type: float.",
    );
  });

  it("strips a blockquote's marker", () => {
    expect(toSpoken("> a quoted line\n> and more")).toBe("a quoted line and more");
  });

  it("speaks nothing for image markdown", () => {
    expect(toSpoken("![alt](https://example.test/i.png)")).toBe("");
  });

  it("reads an escaped tagged word as its words", () => {
    expect(toSpoken("We ship \\<software> to users.")).toBe("We ship software to users.");
    expect(toSpoken("\\<software>")).toBe("software");
    expect(toSpoken("Ship \\<software> before the \\</div> closer.")).toBe(
      "Ship software before the div closer.",
    );
  });

  it.each([
    ["The <div> element.", "The div element."],
    ["Its </div> closer.", "Its div closer."],
    ["A generic <T> parameter.", "A generic T parameter."],
    ["A <br/> void tag.", "A br void tag."],
    ["Set <your-api-key> here.", "Set your-api-key here."],
  ])("keeps the words inside the tag in %j", (text, expected) => {
    expect(sanitizeSpoken(text)).toBe(expected);
  });

  it.each([
    ["a <= b", "a less than or equal to b"],
    ["a >= b", "a greater than or equal to b"],
    ["x -> y", "x to y"],
    ["x => y", "x to y"],
    ["x <- y", "x from y"],
    ["a << b", "a much less than b"],
    ["a >> b", "a much greater than b"],
    ["I <3 tea", "I heart tea"],
    ["a < b", "a less than b"],
    ["a > b", "a greater than b"],
    ["3 <= 4 < 5", "3 less than or equal to 4 less than 5"],
    ["a<b", "a less than b"],
    ["x <30 ms", "x less than 30 ms"],
  ])("reads the operators in %j as words, longest match first", (unit, expected) => {
    expect(toSpoken(unit)).toBe(expected);
  });

  it("keeps an asterisk between spaces", () => {
    expect(toSpoken("It scales by value_0 * 2^{-d} each step.")).toBe(
      "It scales by value_0 * 2^{-d} each step.",
    );
  });

  it("strips a marker touching text and keeps a spaced one", () => {
    expect(sanitizeSpoken("a **b** c ** d")).toBe("a b c ** d");
  });

  it("keeps newlines and collapses whitespace within a line", () => {
    expect(sanitizeSpoken("  one   line .\n\n two\tline ")).toBe("one line.\ntwo line");
  });

  it.each([
    ["The harness parses .wast files.", "The harness parses .wast files."],
    ["Built on **.NET** today.", "Built on .NET today."],
    ["A ratio of .5 holds.", "A ratio of .5 holds."],
    ["It is **done** .", "It is done."],
    ["Wait for it **...**", "Wait for it..."],
  ])("keeps the space before a dot that opens a word in %j", (unit, expected) => {
    expect(toSpoken(unit)).toBe(expected);
  });

  it("reads an autolink as its target", () => {
    expect(toSpoken("Mail <a@b.com> or read <https://x.test> now.")).toBe(
      "Mail a@b.com or read https://x.test now.",
    );
  });

  it("reads table cells through the same inline walk as prose", () => {
    expect(
      toSpoken(
        "| Practice | Description |\n" +
          "| --- | --- |\n" +
          "| **Design doc first** | See the [RFC tradition](https://example.test/rfc) it borrows from. |\n" +
          "| _Pairing on the interface_ | Two engineers argue about \\<software> first |",
      ),
    ).toBe(
      "Practice: Design doc first, Description: See the RFC tradition it borrows from.\n" +
        "Practice: Pairing on the interface, Description: Two engineers argue about software first.",
    );
  });

  it("reads the words of a tag inside a code span", () => {
    expect(toSpoken("Use `<software>` inside a code span.")).toBe(
      "Use software inside a code span.",
    );
  });
});

describe("the cruft test", () => {
  it("matches the title echo past a heading marker", () => {
    expect(isCruft("# My Title", "my title")).toBe(true);
    expect(isCruft("My Title, revisited", "my title")).toBe(false);
  });

  it.each(["-", "❦", "* * *", "§"])("matches %j, which has no letter or digit", (text) => {
    expect(isCruft(text, "")).toBe(true);
  });

  it("keeps a navigation label", () => {
    expect(isCruft("Table of contents", "")).toBe(false);
  });
});

describe("the drop rule", () => {
  it.each(["", "❦", "* * *", "§", "—"])("drops %j, which has no letter or digit", (spoken) => {
    expect(isUnspeakable(spoken)).toBe(true);
  });

  it.each(["日本語の段落です。", "42", "Code sample.", "Ünïcödé"])("keeps %j", (spoken) => {
    expect(isUnspeakable(spoken)).toBe(false);
  });
});
