"""convert -- a document in, titled Sections out. Pure and local: nothing here fetches.

A Section is one heading's worth of text plus its full heading path, so every chunk made from
it knows where it came from. Formats:

  * Markdown / plain text -- split on ATX headings (# .. ######), fenced code left intact.
  * DocC render JSON (Apple developer documentation, including the Human Interface
    Guidelines) -- headings, paragraphs, lists, asides, tables, code and inline references are
    walked structurally, never scraped. References resolve to their titles.
  * HTML -- the main content container is kept (a given selector, else main/article/
    role=main, else body), site chrome is dropped, and the rest is split on its headings.
  * PDF -- text per page via pypdf (BSD); the outline (bookmarks) names the section a page
    belongs to when the PDF has one, otherwise pages are labelled "page N".
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SUPPORTED = {".md", ".markdown", ".txt", ".json", ".html", ".htm", ".pdf"}


@dataclass
class Section:
    path: Tuple[str, ...]          # (document title, heading, subheading, ...)
    text: str
    anchor: Optional[str] = None   # fragment for the source url, when the format has one
    page: Optional[int] = None     # 1-based, PDFs only


@dataclass
class Document:
    title: str
    url: Optional[str]
    sections: List[Section] = field(default_factory=list)


def to_document(path, url: Optional[str] = None, html_selector: Optional[str] = None) -> Document:
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if is_docc(data):
            return from_docc(data, url=url)
        raise ValueError(f"{p.name}: JSON that is not DocC render JSON")
    if ext in (".html", ".htm"):
        return from_html(p.read_text(encoding="utf-8", errors="replace"), url=url,
                         fallback_title=p.stem, selector=html_selector)
    if ext == ".pdf":
        return from_pdf(p, url=url)
    if ext in (".md", ".markdown", ".txt"):
        return from_markdown(p.read_text(encoding="utf-8", errors="replace"), url=url,
                             fallback_title=p.stem)
    raise ValueError(f"{p.name}: unsupported format {ext!r}")


# ---- Markdown ----------------------------------------------------------------------

_ATX = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", s)


def from_markdown(text: str, url: Optional[str] = None, fallback_title: str = "Untitled") -> Document:
    title: Optional[str] = None
    stack: List[Tuple[int, str]] = []
    raw: List[Tuple[Tuple[str, ...], str]] = []
    buf: List[str] = []
    in_code = False

    def flush():
        body = "\n".join(buf).strip()
        if body:
            raw.append((tuple(h for _, h in stack), body))
        buf.clear()

    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
        m = None if in_code else _ATX.match(line)
        if m:
            flush()
            level, heading = len(m.group(1)), m.group(2).strip()
            if title is None and level == 1:
                title = heading
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading))
            continue
        buf.append(line)
    flush()

    title = title or fallback_title
    sections = []
    for path, body in raw:
        if not path or path[0] != title:
            path = (title,) + path
        sections.append(Section(path=path, text=body, anchor=slug(path[-1]) if len(path) > 1 else None))
    return Document(title=title, url=url, sections=sections)


# ---- DocC render JSON ----------------------------------------------------------------

def is_docc(data: Any) -> bool:
    return isinstance(data, dict) and "primaryContentSections" in data and "metadata" in data


def _inline(items: List[Dict[str, Any]], refs: Dict[str, Any]) -> str:
    out = []
    for it in items or []:
        t = it.get("type")
        if t == "text":
            out.append(it.get("text", ""))
        elif t == "codeVoice":
            out.append(it.get("code", ""))
        elif t == "reference":
            ref = refs.get(it.get("identifier", ""), {})
            out.append(it.get("overridingTitle") or ref.get("title")
                       or it.get("identifier", "").rsplit("/", 1)[-1])
        elif t == "link":
            out.append(it.get("title") or it.get("destination", ""))
        elif t == "image":
            alt = (refs.get(it.get("identifier", ""), {}) or {}).get("alt")
            if alt:
                out.append(f"[{alt}]")
        elif "inlineContent" in it:           # emphasis, strong, newTerm, superscript, ...
            out.append(_inline(it["inlineContent"], refs))
    return "".join(out)


def _blocks(blocks: List[Dict[str, Any]], refs: Dict[str, Any]) -> str:
    return "\n".join(x for x in (_block(b, refs) for b in blocks or []) if x.strip())


def _block(b: Dict[str, Any], refs: Dict[str, Any]) -> str:
    t = b.get("type")
    if t == "paragraph":
        return _inline(b.get("inlineContent", []), refs)
    if t in ("unorderedList", "orderedList"):
        lines = []
        for i, item in enumerate(b.get("items", []), 1):
            mark = f"{i}." if t == "orderedList" else "-"
            body = _blocks(item.get("content", []), refs).replace("\n", " ")
            lines.append(f"{mark} {body}")
        return "\n".join(lines)
    if t == "aside":
        label = b.get("name") or (b.get("style") or "note").title()
        return f"{label}: " + _blocks(b.get("content", []), refs).replace("\n", " ")
    if t == "table":
        rows = []
        for row in b.get("rows", []):
            rows.append(" | ".join(_blocks(cell, refs).replace("\n", " ") for cell in row))
        return "\n".join(rows)
    if t == "codeListing":
        return "```\n" + "\n".join(b.get("code", [])) + "\n```"
    if t == "termList":
        return "\n".join(f"- {_inline(i.get('term', {}).get('inlineContent', []), refs)}: "
                         f"{_blocks(i.get('definition', {}).get('content', []), refs)}"
                         for i in b.get("items", []))
    if t == "heading":                         # a heading nested inside a container
        return b.get("text", "")
    if t == "tabNavigator":
        return "\n".join(f"{tab.get('title', '')}: {_blocks(tab.get('content', []), refs)}"
                         for tab in b.get("tabs", []))
    if t == "row":
        return "\n".join(_blocks(col.get("content", []), refs) for col in b.get("columns", []))
    if t == "links":
        return "\n".join(f"- {(refs.get(i, {}) or {}).get('title', i)}" for i in b.get("items", []))
    for key in ("content", "items"):           # unknown containers: keep their text
        if isinstance(b.get(key), list):
            return _blocks(b[key], refs)
    return ""


def from_docc(data: Dict[str, Any], url: Optional[str] = None) -> Document:
    refs = data.get("references") or {}
    title = (data.get("metadata") or {}).get("title") or "Untitled"
    if url is None:
        ident = (data.get("identifier") or {}).get("url") or ""
        m = re.match(r"doc://[^/]+(/.*)", ident)
        if m:
            url = "https://developer.apple.com" + m.group(1)
    sections: List[Section] = []
    stack: List[Tuple[int, str]] = [(1, title)]
    buf: List[str] = []
    anchor: Optional[str] = None

    def flush():
        body = "\n".join(x for x in buf if x.strip()).strip()
        if body:
            sections.append(Section(path=tuple(h for _, h in stack), text=body, anchor=anchor))
        buf.clear()

    abstract = _inline(data.get("abstract") or [], refs)
    if abstract:
        buf.append(abstract)
    for sec in data.get("primaryContentSections") or []:
        for block in sec.get("content") or []:
            if block.get("type") == "heading":
                flush()
                level = int(block.get("level") or 2)
                while len(stack) > 1 and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, block.get("text") or ""))
                anchor = block.get("anchor")
            else:
                buf.append(_block(block, refs))
    flush()
    return Document(title=title, url=url, sections=sections)


# ---- HTML ------------------------------------------------------------------------

_CHROME = ["script", "style", "noscript", "template", "svg", "nav", "footer", "aside", "form",
           "button", "iframe"]


def from_html(html: str, url: Optional[str] = None, fallback_title: str = "Untitled",
              selector: Optional[str] = None) -> Document:
    from bs4 import BeautifulSoup
    from markdownify import markdownify

    soup = BeautifulSoup(html, "lxml")
    page_title = (soup.title.string or "").split("|")[0].strip() if soup.title else ""
    root = soup.select_one(selector) if selector else None
    if root is None:
        root = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
    chrome = list(_CHROME)
    if root is None:
        root = soup.body or soup
        chrome.append("header")               # outside a main container, header is site chrome
    for tag in root.find_all(chrome):
        tag.decompose()
    for img in root.find_all("img"):
        img.replace_with(f"[{img.get('alt')}]" if img.get("alt") else "")
    md = markdownify(str(root), heading_style="ATX", strip=["a"])
    md = re.sub(r"\n{3,}", "\n\n", md)
    return from_markdown(md, url=url, fallback_title=page_title or fallback_title)


# ---- PDF -------------------------------------------------------------------------

def from_pdf(path, url: Optional[str] = None) -> Document:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    meta_title = getattr(reader.metadata, "title", None) if reader.metadata else None
    title = (meta_title or Path(path).stem).strip()
    marks: List[Tuple[int, int, str]] = []    # (page_index, level, title)

    def walk(items, level):
        for it in items:
            if isinstance(it, list):
                walk(it, level + 1)
                continue
            try:
                marks.append((reader.get_destination_page_number(it), level, str(it.title).strip()))
            except Exception:
                continue

    try:
        walk(reader.outline, 1)
    except Exception:
        marks = []
    marks.sort(key=lambda m: (m[0], m[1]))

    sections: List[Section] = []
    stack: List[Tuple[int, str]] = []
    mi = 0
    for i, page in enumerate(reader.pages):
        while mi < len(marks) and marks[mi][0] <= i:
            _, level, name = marks[mi]
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, name))
            mi += 1
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        path = (title,) + (tuple(h for _, h in stack) if stack else (f"page {i + 1}",))
        sections.append(Section(path=path, text=text, page=i + 1))
    return Document(title=title, url=url, sections=sections)
