"""THE EYE S0 -- the incremental transcript indexer, coverage contract built in.

Laws this module carries (from the fenced design + the night's lessons):

  - operator speech lives in `user` turns AND `queue-operation` records
    (operator_speech_hides_in_queue_operation_records) -- both ingest, always.
  - VOICE is conservative: operator | agent | system. Command-caveats, system-reminders,
    task-notifications and isMeta records inside `user` rows are SYSTEM -- the
    false-positive class the success-vocabulary sweep paid for.
  - every event is ADDRESSABLE: event_id = "<session>:<line>", resolving to the verbatim
    record. The grammar's address space; T288's citation-resolver substrate.
  - THE COVERAGE CONTRACT: the report names every file it could not read and refuses to
    claim wholeness past a gap (manifest_complete). A clipped index that reads as whole is
    the laundering class this organ was born from.
  - incremental by (mtime, line-cursor): transcripts are append-only; a re-run ingests
    only appended lines.

The index is a projection: state/eye/eye.db (WAL), rebuildable, never committed.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _REPO_ROOT / "state" / "eye" / "eye.db"

# Markers that make a `user`-typed record SYSTEM, not operator. Same family the
# success-vocabulary extractor learned the hard way (its lens-3 catch).
_SYSTEM_MARKERS = (
    "<command-name>", "<local-command", "Caveat: The messages below",
    "<system-reminder>", "<task-notification", "[SYSTEM NOTIFICATION",
)

_TRANSCRIPT_GLOB = "*.jsonl"


def default_corpus() -> List[Path]:
    """The live transcript manifest: every session JSONL under the harness projects root."""
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return []
    return sorted(p for d in root.iterdir() if d.is_dir()
                  for p in d.glob(_TRANSCRIPT_GLOB))


# ---------------------------------------------------------------- schema
def _connect(db_path: Optional[Path]) -> sqlite3.Connection:
    p = Path(db_path) if db_path else _DEFAULT_DB
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS events(
        event_id TEXT PRIMARY KEY, session TEXT NOT NULL, line INTEGER NOT NULL,
        ts REAL, voice TEXT NOT NULL, type TEXT NOT NULL, text TEXT NOT NULL,
        cwd TEXT, branch TEXT, tokens INTEGER)""")
    con.execute("""CREATE TABLE IF NOT EXISTS ingest_state(
        path TEXT PRIMARY KEY, mtime REAL, lines INTEGER)""")
    con.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
        USING fts5(text, event_id UNINDEXED)""")
    return con


# ---------------------------------------------------------------- extraction
def _texts_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text", "")) for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _parse_ts(raw: Any) -> Optional[float]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _event_from(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One JSONL record -> one event dict (or None when it carries no text)."""
    typ = str(obj.get("type") or "")
    text, voice = "", "system"

    if typ == "user":
        msg = obj.get("message") or {}
        if msg.get("role") == "user":
            text = _texts_from_content(msg.get("content"))
            if obj.get("isMeta"):
                voice = "system"
            elif any(m in text for m in _SYSTEM_MARKERS):
                voice = "system"
            else:
                voice = "operator"
    elif typ == "queue-operation":
        for key in ("prompt", "text", "content"):
            v = obj.get(key)
            if isinstance(v, str) and v.strip():
                text = v
                break
        # The operator-speech law -- UNLESS the queued payload is itself a system block
        # (task-notifications ride this lane too; live S1 smoke caught them polluting the
        # operator axis, the sweep's false-positive class resurfacing one lane over).
        voice = ("system" if any(m in text for m in _SYSTEM_MARKERS) else "operator")
    elif typ == "assistant":
        msg = obj.get("message") or {}
        text = _texts_from_content(msg.get("content"))
        voice = "agent"
    else:
        v = obj.get("content")
        text = v if isinstance(v, str) else _texts_from_content(v)
        voice = "system"

    text = (text or "").strip()
    if not text:
        return None
    return {"ts": _parse_ts(obj.get("timestamp")), "voice": voice, "type": typ,
            "text": text, "cwd": str(obj.get("cwd") or ""),
            "branch": str(obj.get("gitBranch") or ""),
            "tokens": max(1, len(text) // 4)}


# ---------------------------------------------------------------- ingest
def ingest(paths: Optional[List[Path]] = None,
           db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Index the manifest incrementally. The report IS the coverage contract."""
    manifest = [Path(p) for p in (paths if paths is not None else default_corpus())]
    con = _connect(db_path)
    files_indexed, files_failed = 0, []
    events_new = lines_unparsed = 0
    try:
        for f in manifest:
            try:
                st = f.stat()
                cur = con.execute("SELECT mtime, lines FROM ingest_state WHERE path=?",
                                  (str(f),)).fetchone()
                done_lines = int(cur[1]) if cur else 0
                if cur and float(cur[0]) == st.st_mtime and done_lines >= 0:
                    # unchanged since last run -> nothing to read
                    if st.st_mtime == float(cur[0]):
                        files_indexed += 1
                        # still need to detect appended lines when mtime unchanged is
                        # impossible (append changes mtime), so skip is safe
                        continue
                session = f.stem
                n_line = 0
                with open(f, encoding="utf-8", errors="replace") as fh:
                    for n_line, raw in enumerate(fh, start=1):
                        if n_line <= done_lines:
                            continue
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            obj = json.loads(raw)
                        except Exception:
                            lines_unparsed += 1
                            continue
                        ev = _event_from(obj)
                        if ev is None:
                            continue
                        eid = f"{session}:{n_line}"
                        got = con.execute(
                            "INSERT OR IGNORE INTO events(event_id, session, line, ts, "
                            "voice, type, text, cwd, branch, tokens) "
                            "VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (eid, session, n_line, ev["ts"], ev["voice"], ev["type"],
                             ev["text"], ev["cwd"], ev["branch"], ev["tokens"]))
                        if got.rowcount:
                            con.execute(
                                "INSERT INTO events_fts(text, event_id) VALUES(?,?)",
                                (ev["text"], eid))
                            events_new += 1
                con.execute(
                    "INSERT INTO ingest_state(path, mtime, lines) VALUES(?,?,?) "
                    "ON CONFLICT(path) DO UPDATE SET mtime=excluded.mtime, "
                    "lines=excluded.lines", (str(f), st.st_mtime, n_line or done_lines))
                files_indexed += 1
            except OSError as e:
                files_failed.append({"path": str(f),
                                     "why": f"{e.__class__.__name__}: {e}"})
        con.commit()
        total = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        con.close()
    return {"files_seen": len(manifest), "files_indexed": files_indexed,
            "files_failed": files_failed, "events_total": int(total),
            "events_new": events_new, "lines_unparsed": lines_unparsed,
            "manifest_complete": not files_failed,
            "ran_at": round(time.time(), 2)}


# ---------------------------------------------------------------- S1: the grammar door
def _parse_as_of(as_of: Optional[str]) -> Optional[float]:
    """The grammar's 422 rule at this door: a malformed as_of REFUSES with the expected
    shape -- zero rows is never the answer to a malformed selector."""
    if not as_of:
        return None
    try:
        s = str(as_of).strip().replace("Z", "+00:00")
        if len(s) == 10:                      # bare date = end of that day UTC (inclusive)
            s += "T23:59:59+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        raise ValueError(
            f"as_of {as_of!r} is not a date this door reads -- ISO-8601 (YYYY-MM-DD or "
            f"full timestamp); got 0 rows is NOT the answer to a malformed selector")


def find(q: Optional[str] = None, *, who: str = "", kind: str = "", session: str = "",
         as_of: Optional[str] = None, limit: int = 20,
         db_path: Optional[Path] = None) -> Dict[str, Any]:
    """The grammar door (T280, first tenant): facets AND together, q is the phrase
    fallback within the faceted slice, as_of applies the one-sentence temporal law, and
    the ENVELOPE carries degraded honesty + its own token price.

    Degraded case shipped with the door (the formation-trap pattern, applied to time):
    matching events whose ts could not be parsed are UNEVALUABLE under as_of -- excluded,
    and the envelope says so. Absence of a warning means exactly one thing."""
    cutoff = _parse_as_of(as_of)
    con = _connect(db_path)
    try:
        wheres, params = [], []
        if q:
            wheres.append("e.event_id IN (SELECT event_id FROM events_fts "
                          "WHERE events_fts MATCH ?)")
            params.append('"' + str(q).replace('"', " ") + '"')
        if who:
            wheres.append("e.voice = ?"); params.append(who)
        if kind:
            wheres.append("e.type = ?"); params.append(kind)
        if session:
            wheres.append("e.session = ?"); params.append(session)
        base = "FROM events e" + (" WHERE " + " AND ".join(wheres) if wheres else "")
        rows = con.execute(
            f"SELECT e.event_id, e.session, e.line, e.ts, e.voice, e.type, "
            f"substr(e.text, 1, 160), e.tokens {base} ORDER BY e.ts", params).fetchall()
    finally:
        con.close()

    unevaluable = 0
    out = []
    for r in rows:
        rec = {"event_id": r[0], "session": r[1], "line": r[2], "ts": r[3],
               "voice": r[4], "type": r[5], "snippet": r[6], "tokens": r[7]}
        if cutoff is not None:
            if rec["ts"] is None:
                unevaluable += 1
                continue                      # excluded AND counted -- never silent
            if rec["ts"] > cutoff:
                continue
        out.append(rec)

    total = len(out)
    out = out[:max(1, int(limit))]
    degraded = unevaluable > 0
    return {"results": out, "total": total,
            "degraded": degraded,
            "degraded_reason": (f"{unevaluable} matching event(s) lack a parseable "
                                f"timestamp and were unevaluable under as_of"
                                if degraded else None),
            "tokens_returned": sum(r["tokens"] or 0 for r in out),
            "as_of": (datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
                      if cutoff is not None else None)}


def freq(patterns: List[str], db_path: Optional[Path] = None,
         max_refs_per_session: int = 5) -> Dict[str, Any]:
    """S3 -- the frequency axis (HIS axis). A pattern FAMILY (phrasings OR'd, deduped by
    event) becomes counts, sessions, span, per-session refs, and a MECHANICAL verdict.

    The verdict thresholds are written down so they can be argued with:
      0 operator events -> unheard · 1 -> mentioned-once ·
      >=3 across >=2 sessions -> standing-directive · else -> recurring

    The repetition-counts note (2026-08-01) was hand-made because nothing measured this;
    this verb retires that class of hand-count. No LLM anywhere in the path."""
    con = _connect(db_path)
    try:
        seen: Dict[str, Dict[str, Any]] = {}
        for pat in patterns:
            phrase = '"' + str(pat).replace('"', " ") + '"'
            rows = con.execute(
                "SELECT e.event_id, e.session, e.line, e.ts, e.voice "
                "FROM events_fts JOIN events e ON e.event_id = events_fts.event_id "
                "WHERE events_fts MATCH ?", (phrase,)).fetchall()
            for r in rows:
                seen[r[0]] = {"event_id": r[0], "session": r[1], "line": r[2],
                              "ts": r[3], "voice": r[4]}
    finally:
        con.close()

    events = sorted(seen.values(), key=lambda e: (e["ts"] or 0, e["event_id"]))
    ops = [e for e in events if e["voice"] == "operator"]
    by_voice: Dict[str, int] = {}
    for e in events:
        by_voice[e["voice"]] = by_voice.get(e["voice"], 0) + 1
    op_sessions = sorted({e["session"] for e in ops})

    per_session: List[Dict[str, Any]] = []
    for s in sorted({e["session"] for e in events}):
        evs = [e for e in events if e["session"] == s]
        per_session.append({
            "session": s, "events": len(evs),
            "operator_events": sum(1 for e in evs if e["voice"] == "operator"),
            "refs": [e["event_id"] for e in evs][:max_refs_per_session]})

    n_op, n_sess = len(ops), len(op_sessions)
    if n_op == 0:
        verdict = "unheard"
    elif n_op == 1:
        verdict = "mentioned-once"
    elif n_op >= 3 and n_sess >= 2:
        verdict = "standing-directive"
    else:
        verdict = "recurring"

    return {"patterns": list(patterns), "events_total": len(events),
            "operator_events": n_op, "sessions": n_sess, "by_voice": by_voice,
            "first_ts": (ops[0]["ts"] if ops else (events[0]["ts"] if events else None)),
            "last_ts": (ops[-1]["ts"] if ops else (events[-1]["ts"] if events else None)),
            "per_session": per_session, "verdict": verdict}


def stats(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """S5 -- crisp numerics (fence r1 C3: numbers first). TIME-FOG is the share of events
    with no parseable ts: every as_of query is blind to exactly that fraction, so the
    number rides every stats read instead of hiding in a reason string."""
    con = _connect(db_path)
    try:
        total = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        by_voice = dict(con.execute(
            "SELECT voice, COUNT(*) FROM events GROUP BY voice").fetchall())
        by_kind = dict(con.execute(
            "SELECT type, COUNT(*) FROM events GROUP BY type").fetchall())
        sessions = con.execute(
            "SELECT COUNT(DISTINCT session) FROM events").fetchone()[0]
        ts_missing = con.execute(
            "SELECT COUNT(*) FROM events WHERE ts IS NULL").fetchone()[0]
        first, last = con.execute(
            "SELECT MIN(ts), MAX(ts) FROM events WHERE ts IS NOT NULL").fetchone()
    finally:
        con.close()
    return {"events_total": int(total), "sessions": int(sessions),
            "by_voice": {k: int(v) for k, v in by_voice.items()},
            "by_kind": {k: int(v) for k, v in by_kind.items()},
            "ts_missing": int(ts_missing),
            "time_fog": (int(ts_missing) / int(total)) if total else 0.0,
            "first_ts": first, "last_ts": last}


def overview(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """S5 -- the structural region map: sessions as places, each with its counts and span.
    A session whose events are all timeless shows first_ts=None -- shown, never faked."""
    con = _connect(db_path)
    try:
        rows = con.execute(
            "SELECT session, COUNT(*), "
            "SUM(CASE WHEN voice='operator' THEN 1 ELSE 0 END), "
            "MIN(ts), MAX(ts) FROM events GROUP BY session ORDER BY MIN(ts)").fetchall()
    finally:
        con.close()
    return {"sessions": [{"session": r[0], "events": int(r[1]),
                          "operator_events": int(r[2] or 0),
                          "first_ts": r[3], "last_ts": r[4]} for r in rows]}


def get_event(event_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """The address resolves to the verbatim record -- the resolver primitive (T288)."""
    con = _connect(db_path)
    try:
        r = con.execute(
            "SELECT event_id, session, line, ts, voice, type, text, cwd, branch, tokens "
            "FROM events WHERE event_id=?", (str(event_id),)).fetchone()
    finally:
        con.close()
    if not r:
        return None
    return {"event_id": r[0], "session": r[1], "line": r[2], "ts": r[3], "voice": r[4],
            "type": r[5], "text": r[6], "cwd": r[7], "branch": r[8], "tokens": r[9]}
