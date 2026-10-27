import { describe, expect, it } from "vitest";

import { getToc, slugify } from "./toc";

describe("slugify", () => {
  it("makes GitHub-style anchors", () => {
    expect(slugify("The wall (why any of this exists)")).toBe(
      "the-wall-why-any-of-this-exists",
    );
    expect(slugify("Teach-back - status: OPEN")).toBe("teach-back-status-open");
    expect(slugify("The rogues' gallery: what's brutal")).toBe(
      "the-rogues-gallery-whats-brutal",
    );
    expect(slugify("Prefetch: the offense")).toBe("prefetch-the-offense");
  });
});

describe("getToc", () => {
  it("lists level-two headings in order with plain titles", () => {
    const markdown = [
      "intro",
      "## The *cache* ladder",
      "### not this one",
      "## Use `cmov` and [links](https://example.com)",
    ].join("\n");
    expect(getToc(markdown)).toEqual([
      { id: "the-cache-ladder", title: "The cache ladder" },
      { id: "use-cmov-and-links", title: "Use cmov and links" },
    ]);
  });

  it("skips headings inside code fences", () => {
    const markdown = ["```md", "## not a heading", "```", "## Real"].join("\n");
    expect(getToc(markdown)).toEqual([{ id: "real", title: "Real" }]);
  });
});
