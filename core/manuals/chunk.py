"""chunk -- Sections become bounded Chunks, each labelled with where it came from.

Two rules, both about what an agent can use:
  * Tiny SIBLINGS merge (sections with the same parent, e.g. the per-platform notes under
    one heading), so a search hit is rarely a lone sentence. A parent never swallows its
    child: the child keeps its own breadcrumb and #anchor, so a hit cites the exact section.
    A merged sibling keeps its heading as a line in the text, so its words still match.
  * Long sections split at paragraph boundaries (sentences, then hard cuts, only for a
    paragraph that is itself over the limit), so no chunk floods a context window.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from core.manuals.convert import Document, Section

SEP = " › "


@dataclass
class Chunk:
    seq: int
    title: str                 # document title
    breadcrumb: str            # "Doc › Heading › Subheading"
    url: Optional[str]         # source url (or file uri) with the section's #anchor
    page: Optional[int]
    text: str


def _split(text: str, max_chars: int) -> List[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: List[str] = []
    for p in paras:
        if len(p) <= max_chars:
            pieces.append(p)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", p)
        cur = ""
        for s in sentences:
            if len(s) > max_chars:                       # a single run-on "sentence":
                if cur:                                  # cut it by index, in one pass
                    pieces.append(cur); cur = ""         # (slicing the remainder on every cut
                pieces.extend(s[i:i + max_chars]         # was quadratic -- DeepSeek fence)
                              for i in range(0, len(s), max_chars))
                continue
            if cur and len(cur) + 1 + len(s) > max_chars:
                pieces.append(cur); cur = s
            else:
                cur = f"{cur} {s}".strip()
        if cur:
            pieces.append(cur)
    out: List[str] = []
    cur = ""
    for piece in pieces:
        if cur and len(cur) + 2 + len(piece) > max_chars:
            out.append(cur); cur = piece
        else:
            cur = f"{cur}\n\n{piece}" if cur else piece
    if cur:
        out.append(cur)
    return out


def chunk_document(doc: Document, max_chars: int = 1800, min_chars: int = 300,
                   source_uri: Optional[str] = None) -> List[Chunk]:
    base = doc.url or source_uri
    chunks: List[Chunk] = []

    def url_for(sec: Section) -> Optional[str]:
        if not base:
            return None
        return f"{base}#{sec.anchor}" if sec.anchor else base

    def emit(sec: Section, text: str):
        for piece in _split(text, max_chars):
            chunks.append(Chunk(seq=len(chunks), title=doc.title, breadcrumb=SEP.join(sec.path),
                                url=url_for(sec), page=sec.page, text=piece))

    pending: Optional[Section] = None
    pending_text = ""
    for sec in doc.sections:
        if pending is not None:
            siblings = len(sec.path) == len(pending.path) and sec.path[:-1] == pending.path[:-1]
            heading_line = sec.path[-1] if sec.path != pending.path else ""
            addition = (f"{heading_line}\n{sec.text}" if heading_line else sec.text)
            fits = len(pending_text) + 2 + len(addition) <= max_chars
            small = len(pending_text) < min_chars or len(sec.text) < min_chars
            if siblings and fits and small and sec.page == pending.page:
                pending_text = f"{pending_text}\n\n{addition}"
                continue
            emit(pending, pending_text)
        pending, pending_text = sec, sec.text
    if pending is not None:
        emit(pending, pending_text)
    return chunks
