"""Report shelf -- one read surface over every report the fleet has produced.

WHY THIS EXISTS. Reports accumulate faster than anyone can re-read them: 464 in the
atom store by 2026-08-12, plus the ones a session produces that must never reach the
public repo. `AtomFamily.find` answers "which atoms are type=report"; it does not
answer "show me the four frontier sweeps on this arc, side by side, and tell me where
they disagree." This module is that second question.

TWO SHELVES, ONE READ. The fleet shelf is the atom store, whose projections are
git-tracked (`store/docs/report.jsonl`). The private shelf is a directory OUTSIDE the
repo, for reports whose content is personal rather than fleet knowledge. Nothing in
this module can move an item from private to fleet: the shelf a report lives on is
decided by where its bytes are, and minting is the only path onto the fleet shelf.
That asymmetry is deliberate -- a viewer must not be able to publish.

Read-only by construction. No function here writes, mints, or supersedes.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# The private shelf lives outside the repo so that no `git add -A` can sweep it in.
# Override for tests or a different machine; the default is a sibling of the repo root.
PRIVATE_ROOT_ENV = "AURORA_PRIVATE_REPORTS"
_DEFAULT_PRIVATE_ROOT = Path(__file__).resolve().parents[2].parent / "aurora-private" / "reports"

FLEET_SHELF = "fleet"
PRIVATE_SHELF = "private"

# Frontmatter keys we surface as facets. Anything else in the header rides along in
# `extra` rather than being dropped -- a schema that grows should not lose fields here.
_FACETS = ("status", "type", "arc", "date", "title", "gist", "visibility",
           "body_type", "category", "seats", "settled", "origin")


def private_root() -> Path:
    """Where the private shelf lives. Env wins so tests never touch the real one."""
    raw = os.environ.get(PRIVATE_ROOT_ENV)
    return Path(raw) if raw else _DEFAULT_PRIVATE_ROOT


# --------------------------------------------------------------------------- parsing

def parse_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    """Split a projection file into (header, body).

    Accepts the YAML-ish frontmatter the projection writer emits. We parse it by hand
    rather than pulling in a YAML dependency: the writer's output is a flat key/value
    block with JSON-ish scalars, and hand-parsing keeps this module import-light and
    keeps a malformed file from raising deep inside a third-party parser.
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    head_raw = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    header: Dict[str, Any] = {}
    for line in head_raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, val = line.partition(":")
        if not sep:
            continue
        header[key.strip()] = _scalar(val.strip())
    return header, body


def _scalar(val: str) -> Any:
    """Decode one frontmatter value. Unknown shapes stay strings -- never guess."""
    if val in ("null", "~", ""):
        return None
    if val in ("true", "false"):
        return val == "true"
    if val.startswith(("[", "{", '"')):
        try:
            return json.loads(val)
        except ValueError:
            pass
        # The projection writer emits UNQUOTED flow sequences -- `category: [security,
        # method]` -- which are valid YAML and invalid JSON. Returning the raw string
        # here would hand every downstream facet a string that merely looks like a list,
        # so the list stays a list and only genuinely unparseable scalars fall through.
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if not inner:
                return []
            return [p.strip().strip('"\'') for p in inner.split(",") if p.strip()]
        return val.strip('"')
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    return val


# --------------------------------------------------------------------------- shaping

def summarize(atom_or_header: Dict[str, Any], *, shelf: str, body: str = "",
              atom_id: str = "") -> Dict[str, Any]:
    """The card shape the UI lists. Small on purpose: a list view must not carry bodies."""
    header = atom_or_header.get("header", atom_or_header)
    ident = atom_id or atom_or_header.get("id") or header.get("akashic_id") or ""
    cats = header.get("category") or []
    if isinstance(cats, str):
        cats = [c.strip() for c in cats.strip("[]").split(",") if c.strip()]
    seats = header.get("seats") or []
    if isinstance(seats, str):
        seats = [s.strip() for s in seats.strip("[]").split(",") if s.strip()]
    return {
        "id": ident,
        "shelf": shelf,
        "title": header.get("title") or ident,
        "date": header.get("date") or "",
        "arc": header.get("arc"),
        "status": header.get("status") or "current",
        "visibility": header.get("visibility") or ("private" if shelf == PRIVATE_SHELF else "fleet"),
        "category": cats,
        "seats": seats,
        "settled": header.get("settled"),
        "gist": (header.get("gist") or "")[:240],
        "chars": len(body) if body else atom_or_header.get("body_chars", 0),
        "supersedes": atom_or_header.get("supersedes"),
        "superseded": atom_or_header.get("superseded"),
    }


# --------------------------------------------------------------------------- shelves

def _fleet_cards(family) -> List[Dict[str, Any]]:
    atoms = family.find(type_="report")
    out = []
    for a in atoms:
        card = summarize(a, shelf=FLEET_SHELF)
        card["chars"] = len(a.get("body") or "")
        out.append(card)
    return out


def _private_cards(root: Optional[Path] = None) -> List[Dict[str, Any]]:
    root = root or private_root()
    if not root.exists():
        return []
    out = []
    for path in sorted(root.glob("**/*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        header, body = parse_frontmatter(text)
        if not header.get("title"):
            # A file without frontmatter is still a report; derive what we can rather
            # than hiding it. An invisible report is worse than a thinly-labelled one.
            m = re.search(r"^#\s+(.+)$", body or text, re.M)
            header.setdefault("title", m.group(1).strip() if m else path.stem)
            header.setdefault("date", _date_from_name(path.name))
            body = body or text
        card = summarize(header, shelf=PRIVATE_SHELF, body=body,
                         atom_id=header.get("akashic_id") or f"priv_{path.stem}")
        card["path"] = str(path)
        out.append(card)
    return out


def _date_from_name(name: str) -> str:
    m = re.match(r"(\d{4})(\d{2})(\d{2})[_-]", name)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


# --------------------------------------------------------------------------- the API

def list_reports(family=None, *, shelf: Optional[str] = None, category: Optional[str] = None,
                 arc: Optional[str] = None, status: Optional[str] = "current",
                 q: Optional[str] = None, limit: int = 200, offset: int = 0,
                 private_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Cards for the list view, newest first, both shelves merged.

    `shelf` filters to one shelf; None means both. `status=None` includes superseded
    reports -- the default hides them because a shelf that shows every version of every
    report is a shelf nobody scrolls.
    """
    cards: List[Dict[str, Any]] = []
    if shelf in (None, FLEET_SHELF) and family is not None:
        cards.extend(_fleet_cards(family))
    if shelf in (None, PRIVATE_SHELF):
        cards.extend(_private_cards(private_dir))

    if status:
        cards = [c for c in cards if (c.get("status") or "current") == status]
    if category:
        cards = [c for c in cards if category in (c.get("category") or [])]
    if arc:
        cards = [c for c in cards if c.get("arc") == arc]
    if q:
        cards = [c for c in cards if _matches(c, q)]

    cards.sort(key=lambda c: (c.get("date") or "", c.get("id") or ""), reverse=True)
    total = len(cards)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "reports": cards[offset:offset + limit],
        "facets": _facets(cards),
    }


def _matches(card: Dict[str, Any], q: str) -> bool:
    needle = q.strip().lower()
    if not needle:
        return True
    hay = " ".join([
        str(card.get("title") or ""), str(card.get("gist") or ""),
        " ".join(card.get("category") or []), " ".join(card.get("seats") or []),
        str(card.get("arc") or ""), str(card.get("id") or ""),
    ]).lower()
    return all(tok in hay for tok in needle.split())


def _facets(cards: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    cats: Dict[str, int] = {}
    arcs: Dict[str, int] = {}
    shelves: Dict[str, int] = {}
    for c in cards:
        for cat in c.get("category") or []:
            cats[cat] = cats.get(cat, 0) + 1
        if c.get("arc"):
            arcs[c["arc"]] = arcs.get(c["arc"], 0) + 1
        shelves[c["shelf"]] = shelves.get(c["shelf"], 0) + 1
    return {
        "category": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
        "arc": dict(sorted(arcs.items(), key=lambda kv: -kv[1])),
        "shelf": shelves,
    }


def get_report(family=None, atom_id: str = "", *,
               private_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """One report, body included. Looks on both shelves; fleet wins on an id collision."""
    if family is not None and atom_id and not atom_id.startswith("priv_"):
        atom = family.get(atom_id)
        if atom:
            card = summarize(atom, shelf=FLEET_SHELF)
            card["body"] = atom.get("body") or ""
            card["chars"] = len(card["body"])
            card["citations"] = atom.get("citations_out") or []
            return card
    root = private_dir or private_root()
    if root.exists():
        for path in root.glob("**/*.md"):
            stem_id = f"priv_{path.stem}"
            text = path.read_text(encoding="utf-8", errors="replace")
            header, body = parse_frontmatter(text)
            if atom_id in (stem_id, header.get("akashic_id")):
                card = summarize(header or {"title": path.stem}, shelf=PRIVATE_SHELF,
                                 body=body or text, atom_id=atom_id)
                card["body"] = body or text
                card["path"] = str(path)
                return card
    return None


def compare(family=None, left_id: str = "", right_id: str = "", *,
            private_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Two reports side by side: which facets agree, which diverge, how they relate.

    This is the verb the shelf exists for. It deliberately does NOT diff prose --
    two frontier sweeps on the same question share almost no wording while sharing
    every conclusion, so a text diff is noise. Facets, categories and lineage are
    what actually answer "did these two agree".
    """
    left = get_report(family, left_id, private_dir=private_dir)
    right = get_report(family, right_id, private_dir=private_dir)
    if not left or not right:
        missing = [i for i, r in ((left_id, left), (right_id, right)) if not r]
        return {"error": "report not found", "missing": missing}

    same, differ = {}, {}
    for key in ("status", "arc", "visibility", "shelf", "settled", "date"):
        lv, rv = left.get(key), right.get(key)
        (same if lv == rv else differ)[key] = lv if lv == rv else {"left": lv, "right": rv}

    lcats, rcats = set(left.get("category") or []), set(right.get("category") or [])
    lseats, rseats = set(left.get("seats") or []), set(right.get("seats") or [])
    union = lcats | rcats
    return {
        "left": {k: v for k, v in left.items() if k != "body"},
        "right": {k: v for k, v in right.items() if k != "body"},
        "same": same,
        "differ": differ,
        "category": {
            "shared": sorted(lcats & rcats),
            "left_only": sorted(lcats - rcats),
            "right_only": sorted(rcats - lcats),
            "overlap": round(len(lcats & rcats) / len(union), 3) if union else None,
        },
        "seats": {
            "shared": sorted(lseats & rseats),
            "left_only": sorted(lseats - rseats),
            "right_only": sorted(rseats - lseats),
        },
        "lineage": _lineage_relation(left, right),
        "size": {"left_chars": left.get("chars", 0), "right_chars": right.get("chars", 0)},
    }


def _lineage_relation(left: Dict[str, Any], right: Dict[str, Any]) -> str:
    """Name the relation in words the UI can print without further logic."""
    if left.get("superseded") == right.get("id"):
        return "left superseded by right"
    if right.get("superseded") == left.get("id"):
        return "right superseded by left"
    if left.get("supersedes") == right.get("id"):
        return "left supersedes right"
    if right.get("supersedes") == left.get("id"):
        return "right supersedes left"
    if left.get("arc") and left.get("arc") == right.get("arc"):
        return "same arc, independent"
    return "unrelated"
