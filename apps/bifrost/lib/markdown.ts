import { Marked, type Tokens } from "marked";

/**
 * Agent text -> HTML. Bus content is not trusted markup: raw HTML is shown as text and only
 * http(s)/mailto links survive, so a message can never script the console.
 */
const escapeHtml = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

const SAFE_URL = /^(https?:|mailto:)/i;
/** Only command-shaped blocks get a Run button; the server still enforces its own allowlist. */
export const RUNNABLE = /^\s*>?\s*(py(thon3?)?|pytest)(\s|$)/;

const md = new Marked({
  gfm: true,
  breaks: true,
  renderer: {
    html({ text }: Tokens.HTML | Tokens.Tag) {
      return escapeHtml(text);
    },
    link({ href, title, tokens }: Tokens.Link) {
      const label = this.parser.parseInline(tokens);
      if (!SAFE_URL.test(href)) return label;
      const t = title ? ` title="${escapeHtml(title)}"` : "";
      return `<a href="${escapeHtml(href)}"${t} target="_blank" rel="noreferrer noopener">${label}</a>`;
    },
    image({ href, text }: Tokens.Image) {
      return SAFE_URL.test(href) ? `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">${escapeHtml(text || href)}</a>` : escapeHtml(text);
    },
    code({ text }: Tokens.Code) {
      const run = RUNNABLE.test(text) ? '<button type="button" data-act="run">▶ Run</button>' : "";
      return (
        `<div class="code-host"><pre><code>${escapeHtml(text)}</code></pre>` +
        `<div class="code-acts"><button type="button" data-act="copy">Copy</button>${run}</div></div>`
      );
    },
  },
});

export function renderMarkdown(src: string): string {
  return md.parse(src, { async: false });
}
