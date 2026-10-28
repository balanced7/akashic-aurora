/** Table of contents for a walk, read from its markdown so the page can link to every section. */

export interface TocEntry {
  readonly id: string;
  readonly title: string;
}

/** GitHub-style anchor: lower case, punctuation dropped, spaces to hyphens. */
export const slugify = (text: string) =>
  text
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^\p{Letter}\p{Number}\s-]/gu, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");

/** Inline markdown to the text a reader sees: emphasis, code and links unwrapped. */
const plain = (markdown: string) =>
  markdown
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/[*_`]/g, "")
    .replace(/\\(.)/g, "$1")
    .trim();

/**
 * Every `##` heading outside a code fence, in order. The rendered heading derives the same id
 * from its own text (walk-body.tsx), so titles within one walk must be unique.
 */
export const getToc = (markdown: string): TocEntry[] => {
  const entries: TocEntry[] = [];
  let fenced = false;
  for (const line of markdown.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) fenced = !fenced;
    if (fenced) continue;
    const match = /^##\s+(.+?)\s*#*\s*$/.exec(line);
    if (!match?.[1]) continue;
    const title = plain(match[1]);
    entries.push({ id: slugify(title), title });
  }
  return entries;
};
