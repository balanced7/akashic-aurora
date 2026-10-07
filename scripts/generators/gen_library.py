#!/usr/bin/env python3
"""gen_library.py — the library census generator (D2, deepseek 2026-07-22; v2 2026-07-23).

Three projections from one walk:
  1. docs/SHELVES.md          — per-Type census (door 1, v1)
  2. Per-zone README.md       — per-folder tables (door 1b, v2 — the BROWSING face)
  3. docs/ARCS.md             — per-Arc index (door 1c, v2 — "trace our steps")

All three are idempotent and byte-stable when nothing changed (clean diffs).
Never hand-edit any generated file.

    py scripts/generators/gen_library.py              # write SHELVES + READMEs + ARCS
    py scripts/generators/gen_library.py --stdout     # print SHELVES to stdout
    py scripts/generators/gen_library.py --readmes    # write only zone READMEs
    py scripts/generators/gen_library.py --verify     # projection-sha cross-read (drift meter)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent  # T104-M1 depth

# ONE insert, at module scope, before anything can need it. Until 2026-10-07 this file added ROOT to
# sys.path in THREE places (lines 123, 453, 550), every one of them lazily inside a function that
# happened to import from `core`. The default `walk_docs()` path needs none of those, so the
# private-plane filter -- which runs at the entry point, before all three -- was the first code to
# try `from core.trust import private_plane` and the first to get ModuleNotFoundError: run by path,
# `sys.path[0]` is this script's own directory, not the repo root. The filter caught the exception
# and returned the entries unfiltered, which is how a private-plane marker reached docs/SHELVES.md
# with the guard installed and nothing printed. Lazy inserts made correctness depend on call order;
# one eager insert makes it depend on nothing. The three lazy copies are kept where they are: they
# are idempotent, and deleting them is a separate change from making this one correct.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCAN_DIRS = ["docs", "research", "chronicles", "charters"]
SKIP_PREFIXES = [".git", "__pycache__", "node_modules", ".venv", "backups",
                 "dropbox", "data", "state", "sessions", ".claude", ".secrets",
                 "blobs", "model_cache", "temp", ".codex", "ComfyUI-Zluda",
                 "assets", "ollama_data", "rocm-lib",
                 "_archive"]   # M3 2026-07-24: fossils (docs/_archive) stay out of the living census
SKIP_FILES = {"SHELVES.md", "ARCS.md"}   # don't catalog ourselves
SKIP_README_IN = {"docs", "research", "chronicles", "charters"}  # these get full READMEs, never inline-catalogued

# --- header parser ---
_RE_STATUS = re.compile(r"^Status:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_RE_TYPE = re.compile(r"^(?:Class|Type):\s*(.+?)(?:\s*\(.*?\))?\s*$", re.IGNORECASE | re.MULTILINE)
_RE_ARC = re.compile(r"^Arc:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_RE_SEATS = re.compile(r"^Seats:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_RE_DATE = re.compile(r"^Date:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE | re.MULTILINE)
_RE_SUPERSEDED = re.compile(r"(?:superseded by|superseded-by)\s*:?\s*(.+)", re.IGNORECASE)
_RE_HEADING = re.compile(r"^#\s+(.+)$", re.MULTILINE)


#: The provenance line this generator stamps into everything it writes. Its PRESENCE is the only
#: honest answer to "is this file mine to replace?" -- see the zone-README write loop.
STAMP = "Source:** `scripts/generators/gen_library.py`"


def _safe_read(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")[:8000]
    except Exception:
        return None


def _extract(text: str) -> dict:
    """Pull header fields from the top of a .md file."""
    m = _RE_STATUS.search(text)
    status = m.group(1).strip() if m else "unmarked"
    m2 = _RE_TYPE.search(text)
    typ = m2.group(1).strip() if m2 else "untyped"
    m3 = _RE_ARC.search(text)
    arc = m3.group(1).strip() if m3 else ""
    m4 = _RE_SEATS.search(text)
    seats = m4.group(1).strip() if m4 else ""
    m5 = _RE_DATE.search(text)
    date = m5.group(1).strip() if m5 else ""
    m6 = _RE_SUPERSEDED.search(text)
    superseded = m6.group(1).strip() if m6 else ""
    # First heading (not the Status/Type line — the # Title)
    heading = ""
    for line in text.split("\n"):
        hm = _RE_HEADING.match(line.strip())
        if hm and "Status:" not in line and "Type:" not in line and line.strip().startswith("# "):
            heading = hm.group(1).strip()
            break
    return {"status": status, "type": typ, "arc": arc, "seats": seats,
            "date": date, "superseded": superseded, "heading": heading}


def _should_skip(path: Path) -> bool:
    parts = path.parts
    for p in parts:
        if p in SKIP_PREFIXES or p.startswith("."):
            return True
    return path.name in SKIP_FILES


def walk_docs() -> list[tuple[Path, dict]]:
    entries: list[tuple[Path, dict]] = []
    for dname in SCAN_DIRS:
        d = ROOT / dname
        if not d.is_dir():
            continue
        for root, dirs, files in os.walk(str(d)):
            dirs[:] = [x for x in dirs if x not in SKIP_PREFIXES and not x.startswith(".")]
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                fp = Path(root) / fname
                if _should_skip(fp):
                    continue
                text = _safe_read(fp)
                if text is None:
                    entries.append((fp, {"status": "unreadable", "type": "unreadable",
                                         "arc": "", "seats": "", "date": "",
                                         "superseded": "", "heading": ""}))
                    continue
                entries.append((fp, _extract(text)))
    return entries


def _atoms_as_entries() -> list[tuple[Path, dict]]:
    """--from-store (A1 fold-in per deepseek's fence plan): walk ATOMS instead of files.
    Header fields ride the atom directly (no _extract re-parse); entries keep the legacy
    (path, header) shape so every renderer below is untouched. The path is the atom's
    projection home (may not exist yet -- the census is of atoms, not files)."""
    import sys as _sys
    if str(ROOT) not in _sys.path:
        _sys.path.insert(0, str(ROOT))
    from core.foundation.store import create_store
    from core.library.atoms import AtomFamily
    from core.library.projection import projection_relpath
    fam = AtomFamily(create_store(), repo_root=str(ROOT))
    entries: list[tuple[Path, dict]] = []
    for a in fam.find():
        h = a["header"]
        if h.get("visibility") == "local":
            continue  # P3b: redacted/local-only atoms stay out of the PUBLIC census
        h = a["header"]
        entries.append((ROOT / projection_relpath(a), {
            "status": h.get("status", ""), "type": h.get("type", ""),
            "arc": h.get("arc") or "", "seats": ", ".join(h.get("seats", [])),
            "date": h.get("date", ""), "superseded": a.get("superseded") or "",
            "heading": h.get("title", ""),
        }))
    return entries


def _relpath(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _zone_dir(p: Path) -> str:
    """Which scan-dir-level zone a file lives in: docs/, research/drafts/, etc."""
    rel = _relpath(p)
    parts = rel.split("/")
    if len(parts) >= 3 and parts[0] == "research":
        return f"research/{parts[1]}"
    return parts[0] if parts else "root"


# Status sort helpers
_STATUS_ORDER = {"current": 0, "unmarked": 5}
_BADGE = {"current": "🟢", "superseded": "🟠", "fossil": "⚫",
          "unmarked": "⚪", "unreadable": "🔴"}

class LeakGuardUnavailable(RuntimeError):
    """Raised when the private-plane guard cannot run. Named rather than generic so a caller can
    distinguish "the guard refused" from "the generator crashed" -- the first is the guard working.
    """


def _drop_private_plane(entries):
    """Remove private-plane records before ANY catalog is built. Returns (kept, dropped_count).

    core/trust/private_plane.py names this generator's exact class in its own docstring: "any
    generator that walks the merged atom stream and writes to docs/ or store/ becomes an egress
    point", and the sharper half, "existence metadata is a leak" -- a catalog can publish private
    TITLES and IDS while publishing no body at all. Its conclusion is the reason this filter is
    here and not downstream: "THE LEAK PATH IS REGENERATION, NOT AUTHORING."

    Caught live on 2026-10-07: refreshing the 75-day-stale census wrote a private-plane slug into
    both docs/SHELVES.md and research/reviewed/README.md, and the commit gate refused -- correctly,
    and with the right instruction ("regenerate it with the private records excluded ... do NOT
    hand-edit the marker out -- the generator will put it back on the next run").

    Markers are DERIVED from whatever actually lives in private/, never declared, so this needs no
    maintenance as the plane grows. Filtering at the single point where entries enter means every
    downstream catalog -- SHELVES, ARCS, the zone READMEs -- inherits it without each one
    remembering to.

    AND IT FAILS CLOSED, which the first version of this function did not. It opened with
    ``except Exception: return list(entries), 0`` under a comment reading "never fail open loudly",
    and that is exactly what it did -- quietly. Measured hours later: the generator catalogued 1,764
    files, excluded 0, printed nothing, and put a private-plane marker into docs/SHELVES.md,
    docs/ARCS.md and research/reviewed/README.md, because `sys.path[0]` is this script's directory
    when it is run by path and the import raised ModuleNotFoundError. Both failure paths now raise
    `LeakGuardUnavailable` before any catalog is written. See
    tests/test_the_leak_guard_does_not_fail_open.py.
    """
    try:
        from core.trust import private_plane as _pp
        marks = _pp.markers()
    except Exception as exc:                                              # noqa: BLE001
        # FAIL CLOSED. The previous line here was `return list(entries), 0`, with a comment reading
        # "never fail open loudly" -- which is precisely what it did, quietly. An unimportable leak
        # guard is not evidence of a clean corpus; it is no evidence at all, and the two must never
        # render identically. Raising stops the regeneration before a single catalog is written,
        # which is the cheap direction to be wrong in: a stale census costs a reader a day, a
        # published private title cannot be recalled.
        raise LeakGuardUnavailable(
            "the private-plane guard could not be loaded (%s: %s), so NO catalog was written. "
            "This is deliberate: a guard that cannot run must not look like a corpus with nothing "
            "to hide. Fix the import, then re-run -- do not work around it by hand-editing the "
            "catalogs, because the next regeneration puts every marker back."
            % (type(exc).__name__, exc)) from exc
    if not marks:
        # Zero markers is ALSO a refusal, not a clean sweep. markers() derives everything it knows
        # from what actually lives in private/; an empty result means either the plane is genuinely
        # empty or the derivation broke, and this function cannot tell those apart. Same reasoning
        # as the except path above: typed absence, never a silent pass.
        raise LeakGuardUnavailable(
            "the private-plane guard loaded but derived ZERO markers, so it would match nothing and "
            "NO catalog was written. Either private/ is empty (then say so deliberately) or the "
            "derivation in core/trust/private_plane.py broke. 70 markers on 2026-10-07.")
    kept, dropped = [], 0
    for p, h in entries:
        hay = f"{_relpath(p)} {h.get('title') or ''} {h.get('arc') or ''}".lower()
        if any(m.lower() in hay for m in marks):
            dropped += 1
            continue
        kept.append((p, h))
    return kept, dropped


# ---------------------------------------------------------------- SHELVES (v1, unchanged)
#: lowercased group key -> the first spelling actually seen, so headings render as authored.
_type_display: dict[str, str] = {}


def build_census(entries):
    by_type: dict[str, list] = {}
    _type_display.clear()
    for p, h in entries:
        # GROUP case-insensitively, but keep the FIRST SPELLING SEEN for display. A prose-header
        # Type: line can carry a parenthetical containing a path -- docs/WORKING-METHOD.md (a
        # RATIFIED contract) reads "Type: contract (companion to `docs/CONDUCT.md`, not a peer of
        # it)" -- and lowercasing the whole value emitted `docs/conduct.md`, a path git cannot
        # resolve because its index is case-sensitive even where Windows is not. That tripped
        # check_comprehensibility on a file nobody had mis-typed. Grouping does not need the
        # display string flattened.
        _tkey = h["type"].lower()
        _type_display.setdefault(_tkey, h["type"])
        by_type.setdefault(_tkey, []).append((p, h))
    for t in by_type:
        # stable-sort cascade: path asc, then date DESC, then status asc (primary last)
        by_type[t].sort(key=lambda x: _relpath(x[0]))
        by_type[t].sort(key=lambda x: (x[1]["date"] or "0000-00-00"), reverse=True)
        by_type[t].sort(key=lambda x: _STATUS_ORDER.get(x[1]["status"], 3))
    return by_type


def render_shelves(by_type):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# SHELVES — per-type census (auto-generated)", "",
        "Status: current  ",
        f"Type: map (generated) · Arc: library-schema · Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "", f"**Generated:** {now} · **Source:** `scripts/generators/gen_library.py` · **Never hand-edit.**",
        "", "This is door 1 of the library schema (docs/LIBRARY.md).", "", "---", "",
    ]
    for typ in sorted(by_type):
        entries = by_type[typ]
        lines.append(f"## {_type_display.get(typ, typ)} ({len(entries)})")
        lines.append("")
        for p, h in entries:
            rel = _relpath(p)
            badge = _BADGE.get(h["status"], "⚪")
            arc_txt = f" · arc: {h['arc']}" if h["arc"] else ""
            date_txt = f" · {h['date']}" if h["date"] else ""
            lines.append(f"- {badge} `{rel}` — {h['status']}{arc_txt}{date_txt}")
        lines.append("")
    total = sum(len(v) for v in by_type.values())
    lines.append("---")
    lines.append(f"**{len(by_type)} type(s) · {total} file(s)**")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- ZONE READMEs (v2)
_ZONE_PURPOSE = {
    "docs": (
        "Living contracts, maps, plans, and ledgers — the fleet's durable truth. "
        "Files here govern how we build, name things, and navigate the project. "
        "Most files use the `{topic}-{kind}-{YYYY-MM}.md` naming canon."
    ),
    "research": (
        "Research root: field surveys, run-logs, and cross-cutting artifacts. "
        "Subdirectories carry dated work: `drafts/` (in-flight), `reviewed/` (fenced evidence), "
        "`briefs/` (work orders). Naming: `{seat}-{topic}-{kind}-{YYYY-MM-DD}.md`."
    ),
    "research/drafts": (
        "In-flight positions, counters, and designs — not yet reconciled or reviewed. "
        "Files here are working artifacts; they move to `reviewed/` after fence or to `docs/` "
        "after ratification."
    ),
    "research/reviewed": (
        "Fenced evidence: reviews, audits, walk transcripts, frontier sweeps. "
        "Every file here has been through at least one adversarial pass. "
        "Reconciled designs graduate to `docs/`; the reviewed artifact stays as evidence."
    ),
    "research/briefs": (
        "Work orders (briefs) and charters — what seats are asked to build. "
        "Briefs are CONSUMED when the work ships; the artifact is the evidence. "
        "Filing here is the first step of any arc."
    ),
    "chronicles": (
        "Story, reflection, and session memory — the human-readable narrative of the project. "
        "Chronicles are the raw material the Story Atlas draws from. "
        "Session reflections, night plans, and journey docs live here."
    ),
    "charters": (
        "Standing contracts between the fleet and individual seats — charters, CHARTER.md, "
        "and arc-defining design documents. A charter names what a seat owns and how it is gated."
    ),
}

_CANON = {
    "docs": ("`docs/` — `{topic}-{kind}-{YYYY-MM}.md`",),
    "research": ("Naming canon: `{seat}-{topic}-{kind}-{YYYY-MM-DD}.md`",),
    "chronicles": ("Naming: `{topic}-{date}.md` or `{date}-{topic}.md`",),
    "charters": ("Each seat may own a subdirectory or a single CHARTER.md",),
}


def _build_zone_census(entries):
    by_zone: dict[str, list] = {}
    for p, h in entries:
        z = _zone_dir(p)
        by_zone.setdefault(z, []).append((p, h))
    for z in by_zone:
        # stable-sort cascade: path asc, then date DESC, then status asc (primary last)
        by_zone[z].sort(key=lambda x: _relpath(x[0]))
        by_zone[z].sort(key=lambda x: (x[1]["date"] or "0000-00-00"), reverse=True)
        by_zone[z].sort(key=lambda x: _STATUS_ORDER.get(x[1]["status"], 3))
    return by_zone


def _render_zone_readme(zone: str, zone_entries: list, now_str: str) -> str:
    """One zone README.md."""
    purpose = _ZONE_PURPOSE.get(zone, f"Auto-generated catalog for `{zone}/`.")
    canon = _CANON.get(zone, ())
    current = [(p, h) for p, h in zone_entries if h["status"] == "current"]
    archived = [(p, h) for p, h in zone_entries if h["status"] != "current"]
    unclassified = [(p, h) for p, h in zone_entries if h["type"] == "untyped" and h["status"] == "current"]

    lines = [
        f"# {zone}/ — catalog (auto-generated)",
        "",
        purpose,
        "",
    ]
    if canon:
        for c in canon:
            lines.append(c)
        lines.append("")
    lines.extend([
        f"**Generated:** {now_str} · **Source:** `scripts/generators/gen_library.py` · **Never hand-edit.**",
        "",
        "---",
        "",
    ])

    if not current:
        lines.append("*(no current files)*")
        lines.append("")
    else:
        lines.append(f"## Current files ({len(current)})")
        lines.append("")
        lines.append("| File | Type | Arc | Date | Description |")
        lines.append("|------|------|-----|------|-------------|")
        for p, h in current:
            rel = _relpath(p)
            typ = h["type"]
            arc = h["arc"] or "—"
            date = h["date"] or "—"
            desc = (h["heading"] or "").replace("|", "/")[:80]
            lines.append(f"| [`{rel}`]({rel}) | {typ} | {arc} | {date} | {desc} |")
        lines.append("")

    if archived:
        lines.append("<details>")
        lines.append(f"<summary>Archived / superseded ({len(archived)} file(s))</summary>")
        lines.append("")
        lines.append("| File | Status | Type | Date |")
        lines.append("|------|--------|------|------|")
        for p, h in archived:
            rel = _relpath(p)
            badge = _BADGE.get(h["status"], "⚪")
            lines.append(f"| [`{rel}`]({rel}) | {badge} {h['status']} | {h['type']} | {h['date'] or '—'} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if unclassified:
        lines.append("### Unclassified")
        lines.append("")
        for p, h in unclassified:
            rel = _relpath(p)
            lines.append(f"- `{rel}` — no parseable header")
        lines.append("")

    lines.append("---")
    lines.append(f"**{len(current)} current file(s) · {len(archived)} archived**")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- ARCS (v2)
def _build_arc_census(entries):
    by_arc: dict[str, list] = {}
    for p, h in entries:
        a = h["arc"].strip()
        if not a:
            a = "(no arc)"
        by_arc.setdefault(a.lower(), []).append((p, h))
    for a in by_arc:
        # stable-sort cascade: path asc, then date DESC, then status asc (primary last)
        by_arc[a].sort(key=lambda x: _relpath(x[0]))
        by_arc[a].sort(key=lambda x: (x[1]["date"] or "0000-00-00"), reverse=True)
        by_arc[a].sort(key=lambda x: _STATUS_ORDER.get(x[1]["status"], 3))
    return by_arc


def render_arcs(by_arc):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# ARCS — per-arc index (auto-generated)", "",
        "Status: current  ",
        f"Type: map (generated) · Arc: library-schema · Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "", f"**Generated:** {now} · **Source:** `scripts/generators/gen_library.py` · **Never hand-edit.**",
        "",
        "Every file declaring an `Arc:` header, grouped by arc. Current files first; "
        "archived files collapsed. Use this to trace an arc's artifacts across zones — "
        "the same arc may span `docs/`, `research/`, and `charters/`.",
        "", "---", "",
    ]
    for arc_display in sorted(by_arc, key=lambda a: (a == "(no arc)", a)):
        entries = by_arc[arc_display]
        current = [(p, h) for p, h in entries if h["status"] == "current"]
        archived = [(p, h) for p, h in entries if h["status"] != "current"]
        count_str = f"({len(current)})" if not archived else f"({len(current)} + {len(archived)} archived)"
        lines.append(f"## {arc_display} {count_str}")
        lines.append("")
        if not current:
            lines.append("*(all archived)*")
        for p, h in current:
            rel = _relpath(p)
            lines.append(f"- 🟢 `{rel}` — {h['type']}" +
                         (f" · {h['date']}" if h["date"] else "") +
                         (f" · {h['heading'][:60]}" if h.get("heading") else ""))
        if archived:
            lines.append("")
            lines.append(f"<details><summary>{len(archived)} archived file(s)</summary>")
            lines.append("")
            for p, h in archived:
                rel = _relpath(p)
                badge = _BADGE.get(h["status"], "⚪")
                lines.append(f"- {badge} `{rel}` — {h['status']} · {h['type']}" +
                             (f" · {h['date']}" if h["date"] else ""))
            lines.append("")
            lines.append("</details>")
        lines.append("")
    total = sum(1 for a in by_arc if a != "(no arc)")
    lines.append("---")
    lines.append(f"**{total} arc(s) · {sum(len(v) for v in by_arc.values())} file(s)**")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- verify (sweep fold-in)
def _verify_projections() -> int:
    """--verify (T104 sweep fold-in; deepseek spec + kimi's founding audit rule): the
    projection-sha cross-read. BELIEF = the projection frontmatter's akashic_sha;
    STATE = the atom's body_sha. Any mismatch, missing file, or orphan projection is a
    broken-after-import specimen, mechanically detected. Exit 1 on drift (ship-gateable)."""
    import sys as _sys
    if str(ROOT) not in _sys.path:
        _sys.path.insert(0, str(ROOT))
    from core.foundation.store import create_store
    from core.library.atoms import AtomFamily
    from core.library.projection import projection_relpath
    fam = AtomFamily(create_store(), repo_root=str(ROOT))
    atoms = fam.find()
    import hashlib as _hashlib
    sha_re = re.compile(r"^akashic_sha:\s*\"?([0-9a-f]{12})\"?\s*$", re.MULTILINE)
    drift: list[str] = []
    corrupt: list[str] = []
    missing: list[str] = []
    checked = skipped = rehashed = 0
    known_ids: set[str] = set()
    for a in atoms:
        known_ids.add(a["id"])
        # STORE INTEGRITY, the check this function was missing entirely. Everything below compares
        # a RECORDED sha to another RECORDED sha -- belief against belief -- so a body edited
        # outside the atom door passes while hashing to neither. This recomputes from the body,
        # which fam.find() has been returning all along, and is the only line here that can
        # actually detect corruption. Counted separately so a CLEAN verdict names what it hashed:
        # a check that cannot distinguish a healthy corpus from an unverified one is reporting
        # silence, not health.
        _body = a.get("body")
        if _body is not None:
            rehashed += 1
            _calc = _hashlib.sha256(_body.encode("utf-8", "replace")).hexdigest()[:12]
            if _calc != a.get("body_sha"):
                corrupt.append(f"CORRUPT  {a['id']}  (body hashes {_calc}, recorded "
                               f"{a.get('body_sha')})")
        if a["header"].get("visibility") == "local":
            skipped += 1        # P3b redaction: no public projection by design
            continue
        rel = _relpath(ROOT / projection_relpath(a))
        checked += 1
        p = ROOT / rel
        if not p.is_file():
            missing.append(f"MISSING  {rel}  (atom {a['id']})")
            continue
        text = _safe_read(p) or ""      # frontmatter rides the top -- the 8k cap is fine
        m = sha_re.search(text)
        if not m:
            drift.append(f"NO-SHA   {rel}  (frontmatter unreadable)")
        elif m.group(1) != a.get("body_sha"):
            drift.append(f"DRIFT    {rel}  (projection {m.group(1)} != atom {a.get('body_sha')})")
    orphans: list[str] = []
    lib = ROOT / "docs" / "library"
    if lib.is_dir():
        for fp in lib.rglob("*.md"):
            if fp.name == "README.md":
                continue
            if f"art_{fp.stem}" not in known_ids:
                orphans.append(_relpath(fp))
    for row in corrupt:
        print(f"[verify] {row}")
    for row in missing:
        print(f"[verify] {row}")
    for row in drift:
        print(f"[verify] {row}")
    for o in orphans:
        print(f"[verify] ORPHAN   {o}  (no atom in the store)")
    verdict = "CLEAN" if not (corrupt or missing or drift or orphans) else "FINDINGS"
    # EACH KIND COUNTED BY ITS OWN NAME. The previous line called every row "drift row(s)", so a
    # run with 0 sha drift and 8 absent projections reported "8 drift row(s)" -- and those have
    # opposite remedies: a missing projection is a regeneration, a corrupt body is a restore.
    print(f"[gen_library] --verify {verdict}: {checked} projection(s) cross-read, "
          f"{rehashed} body/bodies REHASHED from source, {skipped} local-redacted skipped, "
          f"{len(corrupt)} corrupt, {len(missing)} missing, {len(drift)} sha-drift, "
          f"{len(orphans)} orphan(s)")
    if not rehashed:
        print("[verify] WARNING: 0 bodies were rehashed -- this run compared recorded shas only "
              "and cannot distinguish a healthy corpus from an unverified one")
    return 0 if verdict == "CLEAN" else 1


# ---------------------------------------------------------------- driver
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Library census generator: SHELVES + zone READMEs + ARCS")
    ap.add_argument("--stdout", action="store_true",
                    help="print SHELVES to stdout (legacy mode)")
    ap.add_argument("--readmes", action="store_true",
                    help="write only zone READMEs + ARCS (skip SHELVES)")
    ap.add_argument("--one", default="",
                    help="incremental (A1): render ONE atom's projection file and exit; "
                         "maps stay stale until the next full regen (mirror catches up)")
    ap.add_argument("--from-store", action="store_true", dest="from_store",
                    help="census ATOMS (the store) instead of walking .md files (A1)")
    ap.add_argument("--verify", action="store_true",
                    help="projection-sha cross-read: report DRIFT/MISSING/ORPHAN rows, exit 1 on any")
    args = ap.parse_args(argv)

    if args.verify:
        return _verify_projections()

    if args.one:
        import sys as _sys
        if str(ROOT) not in _sys.path:
            _sys.path.insert(0, str(ROOT))
        from core.foundation.store import create_store
        from core.library.atoms import AtomFamily
        from core.library.projection import render_atom
        fam = AtomFamily(create_store(), repo_root=str(ROOT))
        atom = fam.get(args.one)
        if atom is None:
            print(f"[gen_library] no atom '{args.one}' in the store")
            return 2
        path = render_atom(atom, repo_root=str(ROOT))
        print(f"[gen_library] --one {args.one} -> {path}")
        print("[gen_library] maps (SHELVES/ARCS/READMEs) not updated -- full regen at mirror catches up")
        return 0

    entries = _atoms_as_entries() if args.from_store else walk_docs()
    try:
        entries, _plane_dropped = _drop_private_plane(entries)
    except LeakGuardUnavailable as exc:
        # A refusal, not a crash: one readable line and a non-zero exit, no traceback for the
        # operator to decode, and -- the point -- nothing written. Exit 3 is distinct from 2 (a
        # missing atom) so a caller can tell "the guard stopped me" from "the input was wrong".
        print(f"[gen_library] REFUSED: {exc}")
        return 3
    if _plane_dropped:
        # Counted, never named: printing the titles would be the leak the filter just prevented.
        print(f"[gen_library] private-plane: {_plane_dropped} record(s) excluded from every "
              f"catalog (titles withheld by design)")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # 1) SHELVES.md (type census)
    if not args.readmes:
        by_type = build_census(entries)
        output = render_shelves(by_type)
        if args.stdout:
            print(output)
            return 0
        dest = ROOT / "docs" / "SHELVES.md"
        dest.write_text(output, encoding="utf-8")
        print(f"[gen_library] SHELVES -> {dest}  "
              f"({len(by_type)} type(s), {sum(len(v) for v in by_type.values())} file(s))")

    # 2) Zone READMEs
    by_zone = _build_zone_census(entries)
    written = 0
    kept: list[str] = []
    for zone, zone_entries in sorted(by_zone.items()):
        zone_out = _render_zone_readme(zone, zone_entries, now_str)
        zone_dir = ROOT / zone
        if not zone_dir.exists():
            os.makedirs(str(zone_dir), exist_ok=True)
        readme_path = zone_dir / "README.md"
        # ONLY REPLACE WHAT THIS GENERATOR WROTE. Until 2026-10-07 this write was unconditional and
        # it destroyed 86 lines of hand-written doctrine in research/README.md -- the Research day
        # economics, the loop, the layout table, and the full-fidelity preservation rule -- in a
        # run whose only intent was to refresh a stale catalog. Nothing failed and nothing warned;
        # the loss was visible only in the diff.
        #
        # The stamp below is written into every file this generator produces, so "is this mine to
        # replace?" is answerable from the file's own contents. Stamped: regenerate. Unstamped: a
        # human wrote it, and overwriting is data loss rather than regeneration.
        if readme_path.is_file():
            existing = _safe_read(readme_path) or ""
            if STAMP not in existing:
                kept.append(zone)
                continue
        readme_path.write_text(zone_out, encoding="utf-8")
        written += 1
    print(f"[gen_library] READMEs -> {written} zone(s)")
    # A SILENT SKIP IS THE SAME DEFECT WEARING MANNERS: a protected zone and a stale one must not
    # look identical in the output.
    for z in kept:
        print(f"[gen_library] KEPT     {z}/README.md  (hand-written: no generator stamp, not "
              f"overwritten -- adopt it or add the stamp to have it regenerated)")

    # 3) ARCS.md
    by_arc = _build_arc_census(entries)
    arcs_out = render_arcs(by_arc)
    arcs_dest = ROOT / "docs" / "ARCS.md"
    arcs_dest.write_text(arcs_out, encoding="utf-8")
    arc_count = sum(1 for a in by_arc if a != "(no arc)")
    print(f"[gen_library] ARCS -> {arcs_dest}  "
          f"({arc_count} arc(s), {sum(len(v) for v in by_arc.values())} file(s))")

    return 0


if __name__ == "__main__":
    sys.exit(main())
