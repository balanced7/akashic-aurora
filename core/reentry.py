"""T341: the operator re-entry render — assembly, not charge.

Addressed to Daniil, not to a seat. Born from his own words (INTERIORITY entry 8,
2026-07-29): "I may not remember fully my own excitement and what strings and
threads I was reaching for" — and from QUESTIONS.md, which already named the
settling condition: "Something that lets tired-me trust that peak-me was real."
That is an evidence request, and this module answers it with receipts.

Laws (2026-08-17 fence, Heimdall + Navi, decorrelated; pins in
tests/test_t341_reentry_pins.py):
  ORDER    evidence -> open door -> your move. Never his-words -> his-debt ->
           his-silence ("the render doesn't lie once — it just assembles true
           things into a verdict" — Navi).
  SELECT   by TIME / LIVENESS / POINTER, never by meaning (Heimdall). The only
           operations here are diff, filter, dereference — none can produce a
           proposition about him.
  CITE     every quoted word is verbatim with its eye address, or absent.
  NO GUILT no counts, no ages, no "waiting" on what is his to move; open loops
           stay off the default render (Navi's refusal list).
  LEGEND   the render declares its own bounds — shown / excluded / why
           (his tension-map entry, QUESTIONS.md 2026-07-29).
  CAVEAT   this buys the assembly, not the charge (kimi, on the row).
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

# Mechanical reaching-shape: a disclosed phrase list, never a semantic judgment.
REACHING_PHRASES = (
    "i want", "i wish", "what if", "we need", "i would love", "i am excited",
    "curious", "reaching for", "what do you think",
)

CAVEAT = ("this render buys the assembly, not the charge — whether the spark "
          "returns is yours to report, and only you can (kimi's caveat, "
          "standing on the row)")

_ADDR = "{session}:{line}"


def _utc(ts: Any) -> Optional[float]:
    """ISO string or epoch -> epoch seconds, naive treated as UTC (spine_d4)."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _eye_con(db_path=None):
    from core.eye import index as eye
    return eye._connect(db_path)  # reuse the store; a second surface is the sin


def _newest_operator_event(con, like_any: Optional[List[str]] = None
                           ) -> Optional[Dict[str, Any]]:
    """Newest kind='user' operator event, optionally matching any phrase.

    kind='user' (not queue-operation twins) is the dispatch-brief guard: agent
    briefs pasted into seats wear operator voice (known class, disclosed in the
    legend) and ride the queue plane hardest.
    """
    wheres = ["e.voice = 'operator'", "e.type = 'user'", "e.ts IS NOT NULL"]
    params: List[Any] = []
    if like_any:
        ors = " OR ".join("lower(e.text) LIKE ?" for _ in like_any)
        wheres.append(f"({ors})")
        params.extend(f"%{p}%" for p in like_any)
    row = con.execute(
        "SELECT e.session, e.line, e.ts, e.text FROM events e WHERE "
        + " AND ".join(wheres) + " ORDER BY e.ts DESC LIMIT 1", params
    ).fetchone()
    if row is None:
        return None
    return {"session": row[0], "line": row[1], "ts": row[2], "text": row[3],
            "addr": _ADDR.format(session=row[0], line=row[1])}


def _ledger_moves(since_ts: float) -> List[Dict[str, Any]]:
    import json
    path = ROOT / "state" / "coord" / "tasks.json"
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    rows = d.get("tasks", d) if isinstance(d, dict) else d
    if isinstance(rows, dict):
        rows = list(rows.values())
    moves = []
    for t in rows:
        upd = _utc(t.get("updated"))
        if upd is not None and upd > since_ts:
            moves.append({"id": t.get("id"), "title": _trim(t.get("title") or "", 90),
                          "status": t.get("status"), "commit": t.get("commit")})
    moves.sort(key=lambda m: str(m["id"]))
    return moves


def _commits_since(since_ts: float) -> List[str]:
    iso = datetime.fromtimestamp(since_ts, tz=timezone.utc).isoformat()
    try:
        out = subprocess.run(
            ["git", "log", f"--since={iso}", "--format=%h %s"],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [ln for ln in out.splitlines() if ln.strip()][:40]


def _proposed_doors(limit: int = 5) -> List[Dict[str, str]]:
    import json
    path = ROOT / "state" / "coord" / "tasks.json"
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    rows = d.get("tasks", d) if isinstance(d, dict) else d
    if isinstance(rows, dict):
        rows = list(rows.values())
    prop = [t for t in rows if t.get("status") == "proposed"]
    prop.sort(key=lambda t: _utc(t.get("created")) or 0.0, reverse=True)
    return [{"label": f"{t.get('id')} — {_trim(t.get('title') or '', 80)}",
             "action": f"one word opens this: approve {t.get('id')}"}
            for t in prop[:limit]]


def _question_doors() -> List[Dict[str, str]]:
    path = ROOT / "charters" / "daniel" / "QUESTIONS.md"
    if not path.exists():
        return []
    doors = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"^## \d{4}-\d{2}-\d{2} — (.+)$", ln)
        if not m:
            continue
        title = m.group(1).strip()
        # headers wrap across a second "## " line in this file — rejoin them
        j = i + 1
        while j < len(lines) and re.match(r"^## (?!\d{4}-)", lines[j]):
            title += " " + lines[j][3:].strip()
            j += 1
        if "question" in title.lower() or "desire" in title.lower():
            doors.append({"label": title,
                          "action": "yours whenever it strikes the vein — "
                                    "QUESTIONS.md holds it"})
    return doors[-4:]


def build_reentry(now: Optional[float] = None, show_open_loops: bool = False,
                  since: Optional[str] = None, db_path=None) -> Dict[str, Any]:
    """Assemble the render structure. Diff, filter, dereference — nothing else."""
    con = _eye_con(db_path)
    try:
        last = _newest_operator_event(con)
        since_ts = _utc(since) if since else (last["ts"] if last else None)
        if since_ts is None:
            since_ts = (now or datetime.now(tz=timezone.utc).timestamp()) - 86400.0
        door = _newest_operator_event(con, like_any=list(REACHING_PHRASES))
        from core.eye import index as eye
        fog = eye.stats(db_path).get("time_fog")
    finally:
        con.close()

    built: Dict[str, Any] = {
        "since": {
            "ts": since_ts,
            "iso": datetime.fromtimestamp(since_ts, tz=timezone.utc).isoformat(),
            "last_word": ({"text": last["text"], "addr": last["addr"]}
                          if last else None),
        },
        "evidence": {
            "ledger_moves": _ledger_moves(since_ts),
            "commits": _commits_since(since_ts),
        },
        "open_door": (
            {"text": door["text"], "addr": door["addr"],
             "selected_by": ("most recent operator 'user'-kind utterance "
                             "matching a disclosed phrase list "
                             f"({', '.join(REACHING_PHRASES)}) — by time and "
                             "pattern, never by meaning")}
            if door else None),
        "your_move": _proposed_doors() + _question_doors(),
        "legend": {
            "shown": "ledger rows whose updated-stamp moved since your last "
                     "recorded word; commits landed since then; one verbatim "
                     "utterance of yours selected by disclosed phrase match; "
                     "newest proposed rows and QUESTIONS.md doors, titles only",
            "excluded": "open loops and unanswered threads (off by default — "
                        "ask for them); counts and ages of anything that is "
                        "yours to move; every form of paraphrase; agent chatter",
            "why": "order law: evidence -> open door -> your move — measured "
                   "outcomes first because that is what you ask for at every "
                   "return (eye_freq, 8/8 sessions). Voice labels are "
                   "conservative: a pasted dispatch brief can wear operator "
                   "voice (known class)."
                   + (f" corpus time-fog: {fog}." if fog is not None else ""),
        },
        "caveat": CAVEAT,
    }
    if show_open_loops:
        built["open_loops"] = _question_doors() + _proposed_doors(limit=100)
    return built


def _trim(text: str, cap: int = 420) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= cap else text[:cap].rstrip() + " …"


def render_reentry(built: Dict[str, Any]) -> str:
    L: List[str] = []
    add = L.append
    add("# re-entry — assembled for Daniil")
    add(f"  (since your last word, {built['since']['iso']})")
    add("")
    add("## 1 · WHAT MOVED (measured, from outside yourself)")
    moves = built["evidence"]["ledger_moves"]
    if moves:
        for m in moves:
            sha = f" @{m['commit']}" if m.get("commit") else ""
            add(f"  {m['id']} -> {m['status']}{sha}  {m['title']}")
    else:
        add("  no ledger rows moved — and this line would say so if none had, "
            "so it means exactly that")
    commits = built["evidence"]["commits"]
    if commits:
        add(f"  commits landed: {len(commits)}")
        for c in commits[:12]:
            add(f"    {c}")
    add("")
    add("## 2 · OPEN DOOR (your own reaching, verbatim — one, never a stack)")
    door = built["open_door"]
    if door:
        add(f'  "{_trim(door["text"])}"')
        add(f"      — you, at {door['addr']} (full text resolves there)")
        add(f"      [selected by: {door['selected_by']}]")
    else:
        add("  none matched the phrase list since your last word — an honest "
            "absence, not an empty you")
    add("")
    add("## 3 · YOUR MOVE (each closable in a word; none carries a clock)")
    for item in built["your_move"]:
        add(f"  · {item['label']}")
        add(f"      {item['action']}")
    if built.get("open_loops") is not None:
        add("")
        add("## OPEN LOOPS (you asked for these — they never render by default)")
        for item in built["open_loops"]:
            add(f"  · {item['label']}")
    add("")
    add(f"  legend — shown: {built['legend']['shown']}")
    add(f"  legend — excluded: {built['legend']['excluded']}")
    add(f"  legend — why: {built['legend']['why']}")
    add("")
    add(f"  {built['caveat']}")
    return "\n".join(L)
