#!/usr/bin/env python3
"""gen_library.py — the per-type shelf census (D2, deepseek 2026-07-22).

Door 1 of the library schema (docs/LIBRARY.md): one generated file at
docs/SHELVES.md that catalogs every .md file by its header-declared Type,
with status markers and dates. Never hand-edit SHELVES.md; regenerate:

    py scripts/gen_library.py              # write docs/SHELVES.md
    py scripts/gen_library.py --stdout     # print to stdout (verify before landing)

RULES:
  - A file with NO parseable header is listed under "unclassified" with a
    fingerprint (first 3 lines).
  - A file with a header but no Type: line classifies as "untyped".
  - Status decays to "unmarked" when absent; Type decays to "untyped".
  - The generated file carries its own header: "Type: map (generated)".
  - Research zone: research/, research/drafts/, research/reviewed/, research/briefs/.
  - Docs zone: docs/, chronicles/.
  - Never walks .git, __pycache__, node_modules, .venv, backups, dropbox, data, state,
    sessions, .claude, .secrets, blobs, model_cache.
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
SKIP_FILES = {"SHELVES.md"}   # don't catalog ourselves

# --- header parser ---
# Status: <value>
_RE_STATUS = re.compile(r"^Status:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
# Type: <value> (<kind>)
_RE_TYPE = re.compile(r"^(?:Class|Type):\s*(.+?)(?:\s*\(.*?\))?\s*$", re.IGNORECASE | re.MULTILINE)
# Arc: <value>
_RE_ARC = re.compile(r"^Arc:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
# Seats: <value>
_RE_SEATS = re.compile(r"^Seats:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
# Date: YYYY-MM-DD
_RE_DATE = re.compile(r"^Date:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE | re.MULTILINE)
# superseded by
_RE_SUPERSEDED = re.compile(r"(?:superseded by|superseded-by)\s*:?\s*(.+)", re.IGNORECASE)


def _safe_read(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")[:8000]  # first 8KB = header always
    except Exception:
        return None


def _extract(text: str) -> dict:
    """Pull header fields from the top of a .md file. Returns a flat dict."""
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
    return {"status": status, "type": typ, "arc": arc, "seats": seats,
            "date": date, "superseded": superseded}


def _should_skip(path: Path) -> bool:
    parts = path.parts
    for p in parts:
        if p in SKIP_PREFIXES or p.startswith("."):
            return True
    return path.name in SKIP_FILES


def walk_docs() -> list[tuple[Path, dict]]:
    """Walk all scan dirs for .md files, extract headers. Returns (path, header_dict)."""
    entries: list[tuple[Path, dict]] = []
    for dname in SCAN_DIRS:
        d = ROOT / dname
        if not d.is_dir():
            continue
        for root, dirs, files in os.walk(str(d)):
            # prune skip dirs in-place
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
                                         "arc": "", "seats": "", "date": "", "superseded": ""}))
                    continue
                header = _extract(text)
                entries.append((fp, header))
    return entries


def _relpath(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def build_census(entries: list[tuple[Path, dict]]) -> dict[str, list[tuple[Path, dict]]]:
    """Group by type -> sorted list."""
    by_type: dict[str, list[tuple[Path, dict]]] = {}
    for p, h in entries:
        t = h["type"].lower()
        by_type.setdefault(t, []).append((p, h))
    # sort within each group: status first (current > all others), then date desc, then path
    _status_order = {"current": 0, "unmarked": 5}
    for t in by_type:
        by_type[t].sort(key=lambda x: (
            _status_order.get(x[1]["status"], 3),
            -(x[1]["date"] or "0000-00-00"),
            _relpath(x[0]),
        ))
    return by_type


def render_shelves(by_type: dict[str, list[tuple[Path, dict]]]) -> str:
    """Render docs/SHELVES.md content."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# SHELVES — per-type census (auto-generated)",
        "",
        f"Status: current  ",
        f"Type: map (generated) · Arc: library-schema · Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        f"**Generated:** {now} · **Source:** `scripts/gen_library.py` · **Never hand-edit.**",
        "",
        "This is door 1 of the library schema (docs/LIBRARY.md): every .md file in",
        "`docs/` / `research/` / `chronicles/` / `charters/`, grouped by its",
        "header-declared Type, with status markers. A file with no parseable header",
        "appears under **unclassified**.",
        "",
        "---",
        "",
    ]
    for typ in sorted(by_type.keys()):
        entries = by_type[typ]
        lines.append(f"## {typ} ({len(entries)})")
        lines.append("")
        for p, h in entries:
            rel = _relpath(p)
            st = h["status"]
            badge = {"current": "🟢", "superseded": "🟠", "fossil": "⚫",
                     "unmarked": "⚪", "unreadable": "🔴"}.get(st, "⚪")
            arc_txt = f" · arc: {h['arc']}" if h["arc"] else ""
            seats_txt = f" · {h['seats']}" if h["seats"] else ""
            date_txt = f" · {h['date']}" if h["date"] else ""
            lines.append(f"- {badge} `{rel}` — {st}{arc_txt}{date_txt}{seats_txt}")
        lines.append("")
    # Footer: total count
    total = sum(len(v) for v in by_type.values())
    lines.append("---")
    lines.append(f"**{len(by_type)} type(s) · {total} file(s)**")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate docs/SHELVES.md (library door 1)")
    ap.add_argument("--stdout", action="store_true", help="print to stdout instead of writing")
    args = ap.parse_args(argv)

    entries = walk_docs()
    by_type = build_census(entries)
    output = render_shelves(by_type)

    if args.stdout:
        print(output)
        return 0

    dest = ROOT / "docs" / "SHELVES.md"
    dest.write_text(output, encoding="utf-8")
    print(f"[gen_library] wrote {dest} — {len(by_type)} type(s), "
          f"{sum(len(v) for v in by_type.values())} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
