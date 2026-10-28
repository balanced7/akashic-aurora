/**
 * Citations in a walk are bracketed numbers, "[3][4]", pointing into a numbered References list.
 * Link each number to its reference, and keep a run of them on one line.
 */
interface Node {
  type: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  children?: Node[];
}

const CITATIONS = /(?:\[\d+\])+/g;
const SKIP = new Set(["a", "code", "pre"]);

const text = (node: Node): string =>
  node.type === "text"
    ? (node.value ?? "")
    : (node.children ?? []).map(text).join("");

const linkRun = (run: string): Node => ({
  type: "element",
  tagName: "span",
  properties: { className: ["citations"] },
  children: [...run.matchAll(/\[(\d+)\]/g)].map(([label, number]) => ({
    type: "element",
    tagName: "a",
    properties: { href: `#ref-${number}`, className: ["citation"] },
    children: [{ type: "text", value: label }],
  })),
});

const splitText = (value: string): Node[] => {
  const nodes: Node[] = [];
  let last = 0;
  for (const match of value.matchAll(CITATIONS)) {
    const start = match.index;
    if (start > last)
      nodes.push({ type: "text", value: value.slice(last, start) });
    nodes.push(linkRun(match[0]));
    last = start + match[0].length;
  }
  if (last < value.length)
    nodes.push({ type: "text", value: value.slice(last) });
  return nodes;
};

const linkCitations = (node: Node) => {
  if (!node.children || (node.tagName && SKIP.has(node.tagName))) return;
  node.children = node.children.flatMap((child) => {
    if (child.type === "text" && child.value && CITATIONS.test(child.value)) {
      CITATIONS.lastIndex = 0;
      return splitText(child.value);
    }
    linkCitations(child);
    return [child];
  });
};

/** Give each item of the list after the References heading an id, ref-1 onwards. */
const anchorReferences = (root: Node) => {
  const children = root.children ?? [];
  const heading = children.findIndex(
    (node) => node.tagName === "h2" && text(node).trim() === "References",
  );
  const list = children
    .slice(heading + 1)
    .find((node) => node.type === "element");
  if (heading < 0 || list?.tagName !== "ol") return;
  const start = Number(list.properties?.start ?? 1);
  (list.children ?? [])
    .filter((node) => node.tagName === "li")
    .forEach((item, index) => {
      item.properties = { ...item.properties, id: `ref-${start + index}` };
    });
};

export const rehypeCitations = () => (root: Node) => {
  anchorReferences(root);
  const children = root.children ?? [];
  const end = children.findIndex(
    (node) => node.tagName === "h2" && text(node).trim() === "References",
  );
  // Only the prose: the reference list itself has no citations to link.
  children.slice(0, end < 0 ? undefined : end).forEach(linkCitations);
};
