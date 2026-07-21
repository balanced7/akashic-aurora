"""tally — the blind-counter consensus matrix (W48).

DESIGN + PINS: kimi (tools-hunt #4; tests/test_w48_tally_kimi.py is a full behavioral
spec). BUILD: claude (kimi's headless builder round stalled twice -- built to their pins,
credited, fence-completed). tally <opening> scans research/ for counter files that NAME
the opening, aligns their q-ids (Q1/B3/...), and prints an agree/conflict/partial matrix
so the committer sees 2-of-3 consensus at a glance instead of eyeballing blind counters.

Laws (from kimi's pins):
  TITLE-TRAP DEFUSED -- "B1 stale-directive kill: KEEP" is KEEP, not KILL; the verdict
    follows the FIRST COLON after the q-id (a slice title can carry a vocab word). No
    colon -> first verdict word after the q-id. A prose citation ("the Q7 consensus")
    is never an anchored verdict line.
  ONE-VOICE-NEVER-AGREE -- a row with a single voice reads 'partial', never AGREE: 2-of-3
    cannot be pronounced from one counter (the seat-zero lesson made a law).
  MENTIONS-ARE-NOT-COUNTERS -- a file that names the opening but carries no verdict lines
    (a brief) lands in `mentions`, never as a column.

REFINEMENT (kimi, live builder round 2026-07-21 -- the pins landed after the build and
the first live run on the REAL seat-zero fixture forced four amendments, all pinned):
  VOCAB+ -- the spec vocab missed what kimi's real counter actually says: B2 is disposed
    DONE, Q4 is answered YES (and Q1-Q3 AGREE). This delta adds YES/NO (DONE/VERIFIED and
    the 'open' row-status landed in the fence's own concurrent pass, same fixture catch);
    without them the tool under-reports its own founding round. Flagged for the fence
    (the wish itself named the missing Q-id-header convention; the tool reads leniently,
    convention tightens later).
  OPEN != PARTIAL -- the spec's word is "partial (some silent)" -- SOME. A row with ZERO
    voices (a counterless opening's questions) reads 'open', kept out of the
    partial count: an empty research dir tallies 0/0/0, not a wall of false partials.
  ONE-VOICE SHOUT -- one-voice rows already read partial; the footer now also REFUSES the
    consensus claim outright when < 2 counters filed. The founding wound, printed.
  AUTHOR MERGE -- positions[author] = pos REPLACED an author's whole column per file, so
    a second kimi file (a correction round) would clobber the first's verdicts. Now
    merges per q-id (later file wins per q-id -- a restatement updates, a sibling keeps).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

# verdict vocabulary (case-insensitive); first match after the q-id anchor wins.
_VERDICTS = ("KEEP", "AMEND", "KILL", "ADOPT", "GREEN", "REJECT", "DEFER", "AGREE",
            "DISAGREE", "CONFIRM", "PARTIAL", "DONE", "VERIFIED", "YES", "NO")
_VERDICT_RE = re.compile(r"\b(" + "|".join(_VERDICTS) + r")\b", re.I)
# an anchored q-id at the START of a line's content (after markdown bullet/bold noise).
# the (?!') guard: a possessive ("B4's baseline). Recommendation: adopt W38") is PROSE,
# not a verdict header -- without it the apostrophe satisfies \b and a late prose line
# last-wins-clobbers the real verdict (caught LIVE on kimi's seat-zero counter: B4 read
# ADOPT instead of KEEP; pinned as P10).
_QID_ANCHOR = re.compile(r"^[\s\-*>#]*\**\s*([QB]\d+)\b(?!['’])")


def _author(counter_path: str, opening_path: str) -> str:
    """Seat name from a counter filename, either order: kimi-seat-zero-counter-... -> kimi,
    packet-routing-counter-deepseek-... -> deepseek. Known seats matched anywhere in the
    basename; the earliest-positioned known seat wins (author-first or author-last)."""
    base = os.path.basename(str(counter_path)).lower()
    seats = ("claude", "deepseek", "kimi", "sol", "gemini")
    hits = [(base.find(s), s) for s in seats if s in base]
    return min(hits)[1] if hits else "unknown"


def _slug(opening_path: str) -> str:
    return os.path.splitext(os.path.basename(str(opening_path)))[0].lower()


_TRAILING_DATE = re.compile(r"-\d{4}-\d{2}(?:-\d{2})?$")


def find_counters(opening_path: str, research_dir: str) -> List[str]:
    """Files under research_dir whose TEXT names the opening -- excluding the opening
    itself and files that never mention it. Needles: the basename, its extensionless
    stem, and the date-stripped slug (the brief's 'basename or its slug') -- all long
    enough that a match means 'names this opening', never 'mentions the topic' (the
    loose topic word 'seat-zero' hits 7 files for 2 real counters: rejected, cry-wolf
    law). Sorted for determinism."""
    opening_base = os.path.basename(str(opening_path)).lower()
    stem = os.path.splitext(opening_base)[0]
    slug = _TRAILING_DATE.sub("", stem)
    needles = [n for n in dict.fromkeys((opening_base, stem, slug)) if len(n) >= 8]
    opening_real = os.path.realpath(str(opening_path))
    out: List[str] = []
    for root, _dirs, files in os.walk(research_dir):
        for name in files:
            if not name.lower().endswith(".md"):
                continue
            p = os.path.join(root, name)
            if os.path.realpath(p) == opening_real:
                continue
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    text = f.read().lower()
            except Exception:
                continue
            if any(n in text for n in needles):
                out.append(p)
    return sorted(out)


def _qids(text: str) -> List[str]:
    """Anchored q-ids in a text (keys only, verdict-agnostic) -- the questions an OPENING
    poses, used to seed the matrix rows so a counterless opening still shows its rows."""
    out: List[str] = []
    for raw in str(text or "").splitlines():
        m = _QID_ANCHOR.match(raw)
        if m:
            out.append(m.group(1).upper())
    return out


def extract_positions(text: str) -> Dict[str, str]:
    """{qid: VERDICT} from anchored verdict lines. The q-id must anchor the line; the
    verdict is the first vocab word AFTER THE FIRST COLON if the line has one (title-trap
    law), else the first vocab word after the q-id. Prose q-id citations (not anchored)
    never parse. Later lines overwrite earlier for the same q-id (a summary can restate)."""
    out: Dict[str, str] = {}
    for raw in str(text or "").splitlines():
        m = _QID_ANCHOR.match(raw)
        if not m:
            continue
        qid = m.group(1).upper()
        rest = raw[m.end():]
        # title-trap: if a colon follows the q-id, the verdict lives AFTER it (the slice
        # title before the colon may carry a vocab word we must ignore).
        colon = rest.find(":")
        scan = rest[colon + 1:] if colon != -1 else rest
        v = _VERDICT_RE.search(scan)
        if v:
            out[qid] = v.group(1).upper()
    return out


def matrix(opening_path: str, counter_paths: List[str]) -> Dict[str, Any]:
    """The consensus matrix: authors (counters with >=1 verdict), cells[qid][author]=verdict,
    status[qid] in {AGREE, CONFLICT, partial}, rows (all q-ids seen), mentions (named the
    opening but carried no verdict lines). ONE-VOICE-NEVER-AGREE enforced."""
    authors: List[str] = []
    mentions: List[str] = []
    positions: Dict[str, Dict[str, str]] = {}     # author -> {qid: verdict}
    for cp in counter_paths:
        try:
            with open(cp, encoding="utf-8", errors="replace") as f:
                pos = extract_positions(f.read())
        except Exception:
            pos = {}
        if not pos:
            mentions.append(cp)
            continue
        author = _author(cp, opening_path)
        authors.append(author)
        # merge per q-id (later file wins per q-id): replacing the whole column would let
        # an author's second file (a correction round) clobber their first's verdicts.
        positions.setdefault(author, {}).update(pos)
    authors = sorted(set(authors))
    # rows = the OPENING's questions (seed) UNION every q-id any counter voted on. A
    # counterless opening still shows its rows (all partial); a counter raising a new q-id
    # adds it. Fail-open if the opening is unreadable (rows fall back to counter q-ids).
    seed: set = set()
    try:
        with open(str(opening_path), encoding="utf-8", errors="replace") as f:
            seed = set(_qids(f.read()))
    except Exception:
        seed = set()
    rows = sorted(seed | {q for pos in positions.values() for q in pos},
                  key=lambda q: (q[0], int(q[1:])))
    cells: Dict[str, Dict[str, str]] = {}
    status: Dict[str, str] = {}
    for q in rows:
        row = {a: positions[a][q] for a in authors if q in positions[a]}
        cells[q] = row
        verdicts = set(row.values())
        n = len(row)
        if n == 0:
            status[q] = "open"                 # an opening row no counter has addressed yet
        elif n < 2 or n < len(authors):
            status[q] = "partial"              # one voice, or some author silent -- never consensus
        elif len(verdicts) == 1:
            status[q] = "AGREE"
        else:
            status[q] = "CONFLICT"
    return {"opening": os.path.basename(str(opening_path)), "authors": authors,
            "rows": rows, "cells": cells, "status": status, "mentions": mentions}


def render(m: Dict[str, Any]) -> str:
    authors = m["authors"]
    lines = [f"# tally: {m['opening']}  ({len(authors)} counter(s): "
             f"{', '.join(authors) or 'none'})"]
    if m["rows"]:
        w = max(4, *(len(q) for q in m["rows"]))
        header = "  " + "q".ljust(w) + "  " + "  ".join(a[:8].ljust(8) for a in authors) + "  = status"
        lines.append(header)
        for q in m["rows"]:
            cells = "  ".join((m["cells"][q].get(a, "-"))[:8].ljust(8) for a in authors)
            lines.append("  " + q.ljust(w) + "  " + cells + "  = " + m["status"][q])
    agree = sum(1 for s in m["status"].values() if s == "AGREE")
    conflict = sum(1 for s in m["status"].values() if s == "CONFLICT")
    partial = sum(1 for s in m["status"].values() if s == "partial")
    open_ = sum(1 for s in m["status"].values() if s == "open")
    lines.append(f"  -- {agree} agree / {conflict} conflict / {partial} partial"
                 f" / {open_} open")
    if 0 < len(authors) < 2:
        lines.append("  -- ONE VOICE: no consensus claim (2-of-3 needs >= 2 counters)")
    if m["mentions"]:
        lines.append(f"  (mentions, not counters: "
                     f"{', '.join(os.path.basename(x) for x in m['mentions'])})")
    return "\n".join(lines)


def run(opening_path: str, *, research_dir: str = "research", as_json: bool = False) -> str:
    if not str(opening_path or "").strip():
        raise ValueError("tally needs the opening file to reconcile counters against")
    m = matrix(opening_path, find_counters(opening_path, research_dir))
    if as_json:
        return json.dumps({k: v for k, v in m.items() if k != "mentions"} |
                          {"mentions": [os.path.basename(x) for x in m["mentions"]]}, indent=1)
    return render(m)
