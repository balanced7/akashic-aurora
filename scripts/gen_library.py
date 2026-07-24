#!/usr/bin/env python3
"""gen_library.py — the library census generator (D2, deepseek 2026-07-22; v2 2026-07-23).

Three projections from one walk:
  1. docs/SHELVES.md          — per-Type census (door 1, v1)
  2. Per-zone README.md       — per-folder tables (door 1b, v2 — the BROWSING face)
  3. docs/ARCS.md             — per-Arc index (door 1c, v2 — "trace our steps")

All three are idempotent and byte-stable when nothing changed (clean diffs).
Never hand-edit any generated file.

    py scripts/gen_library.py              # write SHELVES + READMEs + ARCS
    py scripts/gen_library.py --stdout     # print SHELVES to stdout
    py scripts/gen_library.py --readmes    # write only zone READMEs
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent

SCAN_DIRS = ["docs", "research", "chronicles", "charters"]
SKIP_PREFIXES = [".git", "__pycache__", "node_modules", ".venv", "backups",
                 "dropbox", "data", "state", "sessions", ".claude", ".secrets",
                 "blobs", "model_cache", "temp", ".codex", "ComfyUI-Zluda",
                 "assets", "ollama_data", "rocm-lib"]
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

# ---------------------------------------------------------------- SHELVES (v1, unchanged)
def build_census(entries):
    by_type: dict[str, list] = {}
    for p, h in entries:
        by_type.setdefault(h["type"].lower(), []).append((p, h))
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
        "", f"**Generated:** {now} · **Source:** `scripts/gen_library.py` · **Never hand-edit.**",
        "", "This is door 1 of the library schema (docs/LIBRARY.md).", "", "---", "",
    ]
    for typ in sorted(by_type):
        entries = by_type[typ]
        lines.append(f"## {typ} ({len(entries)})")
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
        f"**Generated:** {now_str} · **Source:** `scripts/gen_library.py` · **Never hand-edit.**",
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
        "", f"**Generated:** {now} · **Source:** `scripts/gen_library.py` · **Never hand-edit.**",
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
    args = ap.parse_args(argv)

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
    for zone, zone_entries in sorted(by_zone.items()):
        zone_out = _render_zone_readme(zone, zone_entries, now_str)
        zone_dir = ROOT / zone
        if not zone_dir.exists():
            os.makedirs(str(zone_dir), exist_ok=True)
        readme_path = zone_dir / "README.md"
        readme_path.write_text(zone_out, encoding="utf-8")
        written += 1
    print(f"[gen_library] READMEs -> {written} zone(s)")

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
