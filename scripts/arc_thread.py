#!/usr/bin/env python3
"""arc_thread.py -- door 2 of the library (LIBRARY.md): "trace our steps," materialized.

Given an arc id (a slug like `library-schema` or a ticket like `T094`), gather EVERY
artifact of that arc across all planes and present them as ONE chronological thread:

  - FILE plane:  docs/, research/**, chronicles/ documents whose header `Arc:` field
                 names the arc (the one-facet law: arc lives in the header, not the path,
                 so only a header walk -- never a folder -- can reconstruct an arc).
  - GIT plane:   commits whose subject mentions the arc id.
  - STORE plane: lessons / notes / decisions the event firehose has tagged with the arc
                 (best-effort via agent_cli events --search; skipped cleanly if offline).

Ratified library schema: docs/LIBRARY.md (door 2). Owner: claude (G6 split). This is a
standalone read-only reporter -- no writes, no store mutation. Wire as `agent_cli arc <id>`
later; runnable now as:

    py scripts/arc_thread.py library-schema
    py scripts/arc_thread.py T094 --json
    py scripts/arc_thread.py library-schema --no-store   # file+git only (fast, offline)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Header planes to walk. Kept explicit (not a repo-wide glob) so the thread stays the
# library's documents, not every .md in vendored trees.
DOC_DIRS = ["docs", "research", "chronicles", "charters"]

_ARC_RE = re.compile(r"^\s*(?:Type|Class)\s*:.*?\bArc\s*:\s*([^·|\n]+)", re.I | re.M)
_STATUS_RE = re.compile(r"^\s*Status\s*:\s*([^\n]+)", re.I | re.M)
_DATE_RE = re.compile(r"\bDate\s*:\s*(\d{4}-\d{2}-\d{2})", re.I)


def _norm(arc: str) -> str:
    return arc.strip().lower().replace("_", "-")


def _arc_matches(header_val: str, want: str) -> bool:
    """A header Arc: field may carry several arcs; match any token against `want`."""
    tokens = [_norm(t) for t in re.split(r"[,/]", header_val)]
    w = _norm(want)
    return any(w == t or w in t.split() for t in tokens)


def _read_header(path: str) -> tuple[str, str, str] | None:
    """Return (arc_field, status, date) from the first ~1500 chars, or None."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(1500)
    except OSError:
        return None
    m = _ARC_RE.search(head)
    if not m:
        return None
    sm = _STATUS_RE.search(head)
    # first status token only (before a '(' or '—' aside) -- keeps the thread scannable
    status = re.split(r"\s*[(—]", sm.group(1).strip())[0].strip()[:32] if sm else ""
    date_m = _DATE_RE.search(head)
    date = date_m.group(1) if date_m else ""
    return m.group(1).strip(), status, date


def files_for_arc(want: str) -> list[dict]:
    out = []
    for d in DOC_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                path = os.path.join(dirpath, fn)
                hdr = _read_header(path)
                if not hdr or not _arc_matches(hdr[0], want):
                    continue
                arc_field, status, date = hdr
                rel = os.path.relpath(path, ROOT).replace("\\", "/")
                if not date:  # fall back to mtime for ordering
                    date = datetime.fromtimestamp(
                        os.path.getmtime(path), tz=timezone.utc).date().isoformat()
                out.append({"plane": "file", "date": date, "ref": rel,
                            "status": status, "note": arc_field.strip()})
    return out


def commits_for_arc(want: str) -> list[dict]:
    try:
        r = subprocess.run(
            ["git", "log", "--all", f"--grep={want}", "-i",
             "--pretty=%cd|%h|%s", "--date=short"],
            cwd=ROOT, text=True, capture_output=True, timeout=30)
    except Exception:
        return []
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            date, sha, subj = parts
            out.append({"plane": "git", "date": date, "ref": sha,
                        "status": "", "note": subj[:100]})
    return out


def store_for_arc(want: str) -> list[dict]:
    """Best-effort: lessons/notes/decisions the firehose tagged with the arc."""
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "agent_cli.py"),
             "events", "--search", want, "--limit", "40"],
            cwd=ROOT, text=True, capture_output=True, timeout=45)
    except Exception:
        return []
    if r.returncode != 0 or not r.stdout:
        return []
    out = []
    # parse the human events render: "  [kind] YYYY-MM-DDTHH..  summary"
    for m in re.finditer(r"^\s*\[(\w+)\]\s+(\d{4}-\d{2}-\d{2})\S*\s+(.+)$",
                         r.stdout, re.M):
        kind, date, summary = m.group(1), m.group(2), m.group(3).strip()
        if kind in ("command",):  # git commits already covered by the git plane
            continue
        out.append({"plane": "store", "date": date, "ref": kind,
                    "status": "", "note": summary[:100]})
    return out


def build_thread(want: str, use_store: bool = True) -> list[dict]:
    items = files_for_arc(want) + commits_for_arc(want)
    if use_store:
        items += store_for_arc(want)
    # chronological; undated sinks to the end deterministically
    items.sort(key=lambda x: (x["date"] or "9999", x["plane"], x["ref"]))
    return items


_PLANE_GLYPH = {"file": "DOC", "git": "GIT", "store": "MEM"}


def render(want: str, items: list[dict]) -> str:
    if not items:
        return (f"arc '{want}': no artifacts found across file/git/store planes.\n"
                f"  (check the id -- header Arc: fields, commit subjects, event summaries)")
    lines = [f"# arc-thread: {want}   ({len(items)} artifact(s), oldest first)", ""]
    by_plane = {}
    for it in items:
        by_plane[it["plane"]] = by_plane.get(it["plane"], 0) + 1
    lines.append("  planes: " + " ".join(f"{_PLANE_GLYPH[p]}={n}" for p, n in sorted(by_plane.items())))
    lines.append("")
    for it in items:
        tag = _PLANE_GLYPH.get(it["plane"], "?")
        status = f"  [{it['status']}]" if it.get("status") else ""
        lines.append(f"  {it['date']}  {tag}  {it['ref']}{status}")
        if it["plane"] != "file" and it.get("note"):
            lines.append(f"                   {it['note']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="arc-thread: trace every artifact of an arc")
    ap.add_argument("arc", help="arc id: a slug (library-schema) or ticket (T094)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--no-store", action="store_true", help="file+git only (fast, offline)")
    args = ap.parse_args()

    items = build_thread(args.arc, use_store=not args.no_store)
    if args.json:
        print(json.dumps({"arc": args.arc, "count": len(items), "items": items}, indent=2))
    else:
        print(render(args.arc, items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
