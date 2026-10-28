import { describe, expect, it } from "vitest";

import { rehypeCitations } from "./rehype-citations";

interface Node {
  type: string;
  value?: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: Node[];
}

const t = (value: string): Node => ({ type: "text", value });
const el = (tagName: string, children: Node[], properties = {}): Node => ({
  type: "element",
  tagName,
  properties,
  children,
});

const references = [
  el("h2", [t("References")]),
  t("\n"),
  el("ol", [el("li", [t("One [9]")]), t("\n"), el("li", [t("Two")])]),
];

const run = (root: Node & { children: Node[] }) => {
  rehypeCitations()(root);
  return root;
};

describe("rehypeCitations", () => {
  it("links each citation in a run to its reference and groups the run", () => {
    const root = run({
      type: "root",
      children: [el("p", [t("Fast [1][2], slow.")]), ...references],
    });

    expect(root.children[0]).toEqual(
      el("p", [
        t("Fast "),
        el(
          "span",
          [
            el("a", [t("[1]")], { href: "#ref-1", className: ["citation"] }),
            el("a", [t("[2]")], { href: "#ref-2", className: ["citation"] }),
          ],
          { className: ["citations"] },
        ),
        t(", slow."),
      ]),
    );
  });

  it("anchors the reference list items, honouring a start number", () => {
    const list = el("ol", [el("li", [t("a")]), el("li", [t("b")])], {
      start: 5,
    });
    run({ type: "root", children: [el("h2", [t("References")]), list] });

    expect(list.children?.map((item) => item.properties)).toEqual([
      { id: "ref-5" },
      { id: "ref-6" },
    ]);
  });

  it("leaves code, links and the references themselves alone", () => {
    const code = el("code", [t("a[0][1]")]);
    const link = el("a", [t("[3]")], { href: "/x" });
    const root = run({
      type: "root",
      children: [el("p", [code, link]), ...references],
    });

    expect(root.children[0]).toEqual(el("p", [code, link]));
    expect(JSON.stringify(root.children.slice(1))).not.toContain("citation");
  });

  it("does nothing to a walk without references", () => {
    const root = run({ type: "root", children: [el("p", [t("Plain.")])] });
    expect(root.children).toEqual([el("p", [t("Plain.")])]);
  });
});
