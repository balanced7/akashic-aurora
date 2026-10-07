"""Directive-arc lineage enrichment (Navi, 2026-08-19).

Joins the ratified directive-arc map (his words -> timestamps -> ledger rows)
against the task ledger (rows -> owner/status/commit/files) to produce the
"directives -> actions -> timestamps -> files, reasoning lineage at a glance"
artifact Vandor commissioned.

Runs under the pytest family (isolated exec). Writes the artifact to
research/in-flight/directive-arcs/LINEAGE-at-a-glance.md.

Fresh-eyes disclosure: this seat builds nothing into the product; the output
is a PROJECTION over two existing sources of truth (arc map + ledger). Where
the ledger's files field is empty, the break in the chain is rendered, not
papered over -- the commit sha is the pointer.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARC_MAP = ROOT / "research" / "in-flight" / "directive-arcs" / "DRAFT-directive-arc-map.md"
TASKS = ROOT / "state" / "coord" / "tasks.json"
OUT = ROOT / "research" / "in-flight" / "directive-arcs" / "LINEAGE-at-a-glance.md"

# Row reference in the arc map tables looks like: (T074, done) or (T341, claimed ...)
ROW_REF = re.compile(r"\(T(\d{3}),?\s*([^)]*)\)")
ARC_HEADER = re.compile(r'^## Arc (\d+) \u00b7 "(.+?)"\s*\((.+?)\)\s*$')
# date cell at row start, e.g. | 07-15 | or | 04-12 01:02 | or | (tonight) |
TABLE_ROW = re.compile(r"^\| ([^|]+) \| (.+?) \|$")


def load_tasks():
    data = json.loads(TASKS.read_text(encoding="utf-8"))
    return {t["id"]: t for t in data["tasks"]}


def parse_arcs():
    arcs = []
    current = None
    for line in ARC_MAP.read_text(encoding="utf-8").splitlines():
        m = ARC_HEADER.match(line)
        if m:
            current = {"num": m.group(1), "phrase": m.group(2), "span": m.group(3), "instances": []}
            arcs.append(current)
            continue
        if current is None:
            continue
        tm = TABLE_ROW.match(line)
        if tm and "T" in tm.group(2):
            when = tm.group(1).strip()
            cell = tm.group(2)
            # A cell can hold several instances separated by " · " (e.g. T212/T213).
            # Split so each quote binds to ITS OWN row-ref, not the cell's first.
            refs = list(ROW_REF.finditer(cell))
            for i, rm in enumerate(refs):
                tid = "T" + rm.group(1)
                row_status = rm.group(2).strip()
                seg_start = refs[i - 1].end() if i else 0
                quote = cell[seg_start : rm.start()]
                quote = quote.strip().lstrip("\u00b7").strip().strip("\u201c\u201d\" ").strip()
                current["instances"].append(
                    {"when": when, "tid": tid, "row_status": row_status, "quote": quote}
                )
    return arcs


def short_title(title, limit=90):
    # strip the leading "Tnnn: " and trailing fence/spec boilerplate for a glance render
    t = re.sub(r"^T\d{3}: ", "", title)
    t = t.split(";")[0].split(" -- ")[0]
    return (t[: limit - 1] + "\u2026") if len(t) > limit else t


def build():
    tasks = load_tasks()
    arcs = parse_arcs()
    lines = []
    lines.append("# Directive Lineage at a Glance")
    lines.append("")
    lines.append("Projection: arc map (his words, timestamps) \u00d7 task ledger (owner, status, commit, files).")
    lines.append("Built by Navi 2026-08-19, exec-grant session. Sources: DRAFT-directive-arc-map.md (ratified")
    lines.append("2026-08-18) + state/coord/tasks.json @ seq 364. Nothing here is new truth -- it is a JOIN over")
    lines.append("two existing truths. Where the chain breaks (ledger files field empty), the break is shown.")
    lines.append("")
    breaks = 0
    served_rows = 0
    for arc in arcs:
        lines.append(f"## Arc {arc['num']} \u00b7 \u201c{arc['phrase']}\u201d  ({arc['span']})")
        lines.append("")
        lines.append("| When | His words | Row | State | Owner | Commit | Files |")
        lines.append("|---|---|---|---|---|---|---|")
        for inst in arc["instances"]:
            t = tasks.get(inst["tid"])
            if t is None:
                lines.append(
                    f"| {inst['when']} | {inst['quote']} | {inst['tid']} | NOT IN LEDGER | \u2014 | \u2014 | \u2014 |"
                )
                breaks += 1
                continue
            served_rows += 1
            files = t.get("files") or []
            commit = t.get("commit")
            status = t.get("status") or "\u2014"
            if files:
                fcell = "<br>".join(files)
            elif status in ("approved", "claimed", "proposed", "parked", "abandoned") and not commit:
                # open/parked row: the action has not landed, so there are no files yet -- not a break
                fcell = f"\u2014 (row {status}; no commit yet)"
            elif commit == "HEAD":
                fcell = "\u26a0 files not recorded; commit logged as HEAD (unresolved pointer)"
                breaks += 1
            else:
                fcell = f"\u26a0 files not recorded \u2014 commit {commit or 'none'} is the pointer"
                breaks += 1
            commit_cell = commit or "\u2014"
            owner = t.get("owner") or "\u2014"
            quote = inst["quote"] if inst["quote"] else short_title(t["title"])
            lines.append(
                f"| {inst['when']} | {quote} | {inst['tid']} | {status} | {owner} | {commit_cell} | {fcell} |"
            )
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## What the join shows")
    lines.append("")
    lines.append(f"- {served_rows} directive instances resolve to live ledger rows.")
    lines.append(f"- {breaks} TRUE breaks in the files chain: the row is DONE (work landed) but the files")
    lines.append("  field is empty. Open/approved/claimed rows with no commit yet are NOT breaks -- the action")
    lines.append("  has not happened, so there are no files to record.")
    lines.append("- Two break shapes: (a) commit sha present but files never filled in -- the commit carries the")
    lines.append("  truth, the ledger does not; (b) commit logged as the literal string HEAD -- an unresolved")
    lines.append("  pointer that will rot the moment HEAD moves (T206, T212, T204, T215 carry this shape).")
    lines.append("- If 'reasoning lineage at a glance' is to be a standing surface, the files field is the seam")
    lines.append("  that wants a git-backed backfill verb: resolve each done row's commit to its touched files")
    lines.append("  once, write them back, and the chain closes. HEAD-shaped commits want resolving to their")
    lines.append("  sha at write time, before the pointer rots.")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return served_rows, breaks


def test_lineage_projection_builds():
    served, breaks = build()
    assert served > 0, "no arc instances resolved to ledger rows -- the join key drifted"
    assert OUT.exists()
    body = OUT.read_text(encoding="utf-8")
    assert "Arc 1" in body and "Arc 8" in body
    print(f"\nlineage projection: {served} rows served, {breaks} chain breaks -> {OUT}")
