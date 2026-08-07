"""timeline -- one chronological SET across domains (T211).

THE SIX TURNS THIS EXISTS TO SAVE, measured 2026-08-06. A wake watcher kept exiting
instantly and I chased it across six turns -- arm, drain, arm, ack, arm, drain both lanes,
arm, pause the fleet, skip cursors, arm. What I could not see from inside was that MY OWN
dogfood asks were manufacturing the pending mail I kept draining. Every fact was already
recorded, in four separate domains, and nothing put them in one column:

    00:12  claude    ask --peer deepseek          (my own)
    00:12  deepseek  reply "ALIVE"                (lands in my inbox)
    00:13  claude    wake arm -> seeded over 7 undrainable
    00:14  claude    drain legacy -> parked 7
    00:15  claude    wake arm -> seeded over 10 undrainable   <- it GREW

The growth, in one column, IS the diagnosis. Forensics calls this a super timeline
(plaso/log2timeline): you do not search for the cause -- you line the domains up by time
and the cause becomes visible.

IT RETURNS A SET, NOT A RENDERING. Daniil's correction, adopted: he pushed back on
"one result set, many lenses" because the value at his work comes from CROSS-MATCHING what
one system has and another does not. He is right, and the proof is in this repo -- nearly
every guard we own is already a cross-domain set difference: check_door_parity (CLI verbs
minus MCP verbs minus ToolBox verbs), check_wiring (tracked files minus reachable files),
suite_baseline.delta, T122's unmapped kinds. Four of our best instruments, one shape, each
hand-built as a one-off. So this emits rows a future `compare` can diff.

COVERAGE IS LOAD-BEARING HERE ABOVE ALL. A set difference is only as true as the coverage
of BOTH sides: A minus B, where B was partly collected, MANUFACTURES findings. I shipped
precisely that bug today and caught it four minutes later, when a three-file test run made
ten baseline failures look "fixed". So every result names which domains were read, which
FAILED, and how many rows each produced -- and a domain that could not be read is never
silently absent. "Nothing happened there" and "I could not look there" are different facts.
"""
from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Named blindness, structural. A timeline that confesses nothing claims to be the whole
#: story, and a whole story is exactly what a partial merge is not.
BLIND = [
    "only domains listed in coverage.read were consulted; a domain in coverage.failed "
    "contributed NOTHING and its absence must not read as 'nothing happened there'",
    "rows without a resolvable timestamp are kept and sorted LAST, never dropped and "
    "never coerced to epoch 0 -- 'when unknown' is not 'did not happen'",
    "clock skew between domains is not corrected: git commit times, event stamps and "
    "file mtimes come from different writers and may disagree by seconds",
]


def _epoch(v: Any) -> Optional[float]:
    """Best-effort epoch. None when undateable -- never 0, which would silently move
    unknown-time evidence to the dawn of the record and rewrite the story."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v) or None
    s = str(v).strip()
    # Bare epoch strings first: git's %at is "1786079938", and to_epoch parses ISO, so it
    # returned 0.0 for every commit -- stamping the whole of git at 1970 and letting the
    # `since` filter drop it. Caught live on this module's first real run, one function
    # below a pin that forbids exactly this coercion. A pin that supplies its own dict
    # inputs never exercises the parse, which is the third instance of that today.
    if s.replace(".", "", 1).isdigit():
        try:
            # `or None` matters: "0" is undateable by the same rule as a parser's 0.
            return float(s) or None
        except ValueError:
            return None
    try:
        from core.foundation.timeutil import to_epoch
        got = to_epoch(s)
        # 0 from a parser means "could not read", not "1 Jan 1970". Trusting it is how
        # undateable evidence silently becomes the oldest evidence.
        return float(got) if got else None
    except Exception:
        return None


def _norm(row: Dict[str, Any], domain: str) -> Dict[str, Any]:
    return {"ts": _epoch(row.get("ts")), "domain": domain,
            "actor": row.get("actor") or "", "kind": row.get("kind") or "",
            "summary": str(row.get("summary") or "")[:300],
            "ref": row.get("ref") or ""}


# ------------------------------------------------------------------ domain sources
def _events_rows(since: Optional[float] = None, agent: str = "", **_) -> List[Dict]:
    from core.events.event_log import EventLog
    out = []
    for ev in (EventLog().scan(agent=agent) if agent else EventLog().scan()) or []:
        out.append({"ts": ev.get("at"), "actor": ev.get("agent_id") or "",
                    "kind": ev.get("kind") or "event",
                    "summary": ev.get("summary") or ev.get("message") or "",
                    "ref": ev.get("_ref") or ev.get("id") or ""})
    return out


def _git_rows(since: Optional[float] = None, limit: int = 200, **_) -> List[Dict]:
    r = subprocess.run(["git", "log", f"-{int(limit)}", "--format=%H%x1f%at%x1f%an%x1f%s"],
                       cwd=_ROOT, capture_output=True, text=True, timeout=30,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "git log failed").strip()[:200])
    out = []
    for line in (r.stdout or "").splitlines():
        parts = line.split("\x1f")
        if len(parts) != 4:
            continue
        sha, at, who, subj = parts
        out.append({"ts": at, "actor": who, "kind": "commit", "summary": subj,
                    "ref": sha[:12]})
    return out


def _task_rows(since: Optional[float] = None, **_) -> List[Dict]:
    import json
    with open(os.path.join(_ROOT, "state", "coord", "tasks.json"), encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for t in data.get("tasks", []):
        for ev in (t.get("history") or t.get("events") or []):
            out.append({"ts": ev.get("at") or ev.get("ts"),
                        "actor": ev.get("by") or t.get("owner") or "",
                        "kind": f"task:{ev.get('to') or ev.get('status') or 'change'}",
                        "summary": f"{t.get('id')} {str(t.get('title') or '')[:120]}",
                        "ref": str(t.get("id") or "")})
    return out


def default_sources() -> List[Tuple[str, Callable]]:
    """The domains, registered BY NAME so a missing one shows up in coverage rather than
    being quietly absent from the design."""
    return [("events", _events_rows), ("git", _git_rows), ("tasks", _task_rows)]


def gather(*, sources: Optional[List[Tuple[str, Callable]]] = None,
           since: Optional[float] = None, **kw) -> Dict[str, Any]:
    """Merge every domain into one time-ordered set. Never raises.

    Returns {rows, coverage, blind}. `rows` is DATA (dicts a later compare can diff),
    never a rendering. `coverage` names read / failed / per-domain counts / undated /
    window -- because a set difference is only as true as the coverage of both sides.
    """
    srcs = sources if sources is not None else default_sources()
    rows: List[Dict[str, Any]] = []
    read: List[str] = []
    failed: Dict[str, str] = {}
    counts: Dict[str, int] = {}

    for name, fn in srcs:
        try:
            got = fn(since=since, **kw) or []
        except Exception as e:
            # Named, never silent: an unreadable domain is a FACT about the report.
            failed[name] = f"{e.__class__.__name__}: {e}"
            continue
        normed = [_norm(r, name) for r in got]
        if since is not None:
            normed = [r for r in normed if r["ts"] is None or r["ts"] >= float(since)]
        read.append(name)
        counts[name] = len(normed)
        rows.extend(normed)

    undated = sum(1 for r in rows if r["ts"] is None)
    # Undated rows sort LAST. Coercing them to 0 would place unknown-time evidence at the
    # beginning of the record, which is a lie told by a sort key.
    rows.sort(key=lambda r: (r["ts"] is None, r["ts"] if r["ts"] is not None else 0.0))

    blind = list(BLIND)
    for name, why in failed.items():
        blind.append(f"domain '{name}' could NOT be read ({why}) -- it contributed zero "
                     f"rows, which is not the same as having none")
    return {"rows": rows, "blind": blind,
            "coverage": {"read": read, "failed": failed, "counts": counts,
                         "undated": undated, "since": since,
                         "as_of": time.time(), "n": len(rows)}}
