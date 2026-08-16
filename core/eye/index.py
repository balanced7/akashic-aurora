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
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _REPO_ROOT / "state" / "eye" / "eye.db"

# Markers that make a `user`-typed record SYSTEM, not operator. Same family the
# success-vocabulary extractor learned the hard way (its lens-3 catch).
_SYSTEM_MARKERS = (
    "<command-name>", "<local-command", "Caveat: The messages below",
    "<system-reminder>", "<task-notification", "[SYSTEM NOTIFICATION",
    # The harness writes this into a `user` record when the operator hits escape. It is a
    # record ABOUT him, not FROM him -- and it recurs often enough to rank as one of his
    # most-repeated "phrases" until it was excluded (found 2026-08-11 by the directive
    # watcher, which surfaced it as a top standing directive: the false-positive class the
    # marker list already existed to fight, with one member missing).
    "[Request interrupted",
    # The compaction summary the harness writes into a `user` record when a session runs
    # out of context. It is the largest false-positive in the class: it is LONG and it
    # restates the whole conversation, so every phrase in it reads as something he said,
    # in his voice, at that timestamp. Found 2026-08-11 when the directive watcher ranked
    # a compaction preamble as one of his top standing directives.
    "This session is being continued from a previous conversation",
    "Please continue the conversation from where we left it off",
)

_TRANSCRIPT_GLOB = "*.jsonl"

# T313: the archive roots come from ONE declaration shared with the tool that writes them.
# Imported defensively: the indexer must still work if config is unavailable, but a missing
# constant is a shrunken corpus, so it is reported by corpus_coverage() rather than swallowed.
try:
    import sys as _sys
    if str(_REPO_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_REPO_ROOT))
    from config import TRANSCRIPT_ARCHIVE_ROOTS
except Exception:                                    # pragma: no cover - config is a leaf module
    TRANSCRIPT_ARCHIVE_ROOTS = []

# Subagent transcripts are INDEXED (their findings are real) but counted separately, because
# ~5x more of them exist than operator-bearing sessions and an unlabelled mix makes a terse
# operator look verbose. Same markers the archiver uses to EXCLUDE them; here they only tag.
_SUBAGENT_MARKERS = ("subagents", "workflows")


def is_subagent_path(path: Any) -> bool:
    """Is this transcript a SUBAGENT's, by its source path? The one declaration.

    The 2026-08-16 authorship fix (RED a5afd360). The distinction existed here and was
    only ever used to COUNT (corpus_coverage),
    never persisted, so no consumer could apply it -- and the consumers that needed it most
    are the ones reading `voice='operator'`. In a subagent transcript the whole brief lands
    as a `user` record, so `_event_from` labels it operator by its own rule and wrongly in
    fact: the author is the dispatching agent, not the human.

    Measured 2026-08-16, the first live run after T313 made 430 of these reachable: 419 of
    523 operator-voice sessions were subagent briefs. Eleven percent of the RECORDS and
    eighty percent of the SESSIONS -- and `directives.unheeded()` ranks by sessions, so a
    104-voter fan carrying one authored brief outranked everything the operator has ever
    said. The organ built to keep his directives from evaporating was burying them under
    our own prompts, and it got worse the moment the corpus got better."""
    return any(m in str(path).lower() for m in _SUBAGENT_MARKERS)

# Bump when the events schema changes shape.
#
# THE EVENTS TABLE IS NOT DISPOSABLE, and this cost real history to learn (2026-08-11).
# v2 shipped as a wipe-and-rebuild on the design's own words -- "the index is a projection,
# rebuildable from source" -- and the first live run destroyed >=219 events from two
# sessions whose transcripts had rotated off disk hours earlier. The premise was false by
# measurement: the corpus shrank 85 -> 83 files DURING the session that wiped it. For a
# rotated session the projection IS the archive, and an archive you can rebuild from a
# source that no longer exists is just a deletion with extra steps.
#
# So migrations ADD, never DROP. Derived tables (pyramid, edges) are genuinely disposable
# and may be rebuilt freely; `events` may not. Rows whose source file is gone keep NULL in
# any column added later, and that NULL is reported as unevaluable rather than as absence.
_SCHEMA_VERSION = 5


def utterance_key(session: str, text: str) -> Tuple[str, str]:
    """THE UTTERANCE LAW, in one place: an utterance is not a row, it is the SET of records
    carrying it -- and two records carry the same utterance when they hold the same text in
    the same session.

    The harness records each operator turn more than once (the queue-operation enqueue and
    dequeue, plus the delivered `user` twin: identical text, 1.6-17s apart). S2's pyramid
    learned that inline for its digests and `eye freq` had not, counting records as if they
    were utterances and inflating its verdicts across its own threshold. Both now call
    this, so the law has ONE definition
    (convergent_fixes_describe_meaning_not_location_or_membership).

    Session-scoped deliberately: the same sentence in two sessions is two utterances --
    that is exactly the repetition `freq` measures, and collapsing it would destroy the
    axis rather than clean it."""
    return (session, " ".join((text or "").split()))


def default_corpus() -> List[Path]:
    """The transcript manifest: every session JSONL the harness still holds, PLUS the
    rescued archive.

    The second half is not optional. Transcripts rotate off the harness disk, and a rebuild
    that reads only the live directory silently drops every rescued session -- which is
    exactly what happened twice on 2026-08-11, the second time to the very sessions
    recovered from a shadow copy hours earlier. A corpus definition that excludes the
    archive makes every rebuild a partial one, quietly."""
    return sorted(p for _label, _base, files in _corpus_roots() for p in files)


def _corpus_roots() -> List[Any]:
    """(label, files) per root, deduped by filename, in precedence order.

    T313. Three faults fixed here, all of the same family -- a reader that could not see what a
    writer produced:

      1. THE ARCHIVE WAS THE WRONG ONE. This read state/eye/recovered (12 files) while
         scripts/ops/archive_transcripts.py wrote to config.TRANSCRIPT_ARCHIVE_ROOTS (102 files,
         20 of them no longer anywhere else). Ninety sessions were unreachable. Both sides now
         read one declaration and a pin asserts they agree.
      2. THE LIVE GLOB WAS ONE LEVEL. `d.glob()` cannot see projects/<id>/subagents/*.jsonl --
         404 of them at time of writing, holding every research agent's findings. rglob reaches
         them. They are INDEXED, not excluded, because the index already carries a `voice` field
         that separates operator from agent; excluding them would hide real findings, and
         including them silently would drown operator-speech analysis in agent prompts (the
         measured failure: naive sampling concludes he is verbose when he is terse).
      3. NOTHING PUBLISHED COVERAGE. A root that vanishes or a glob that narrows used to return
         a smaller list with no signal. corpus_coverage() now names every root and its count, so
         a shortfall is a number rather than a silence.

    Dedup is by FILENAME and precedence is live > archive > rescued: the live copy is the one
    still being appended to, so an archived copy of the same session must never shadow it."""
    roots: List[Any] = []
    seen: set = set()

    def _take(label: str, base: Path, files) -> None:
        picked = [p for p in sorted(files) if p.name not in seen]
        seen.update(p.name for p in picked)
        roots.append((label, str(base), picked))

    live = Path.home() / ".claude" / "projects"
    if live.is_dir():
        _take("live", live, live.rglob(_TRANSCRIPT_GLOB))
    for base in TRANSCRIPT_ARCHIVE_ROOTS:
        b = Path(base)
        if b.is_dir():
            _take("archive", b, b.glob(_TRANSCRIPT_GLOB))
    rescued = _REPO_ROOT / "state" / "eye" / "recovered"
    if rescued.is_dir():
        _take("rescued", rescued, rescued.glob(_TRANSCRIPT_GLOB))
    return [(lbl, base, files) for lbl, base, files in roots]


def corpus_coverage() -> Dict[str, Any]:
    """What the corpus definition actually reached -- the frame that must ship with the number.

    Lesson a_coverage_contract_must_state_the_scope_it_globs_not_just_the_files_it_read, whose own
    example is THE EYE printing "83/83 manifest_complete" while globbing one level and seeing 82
    of 443 files on disk. A count without its frame is not a coverage claim."""
    rows = _corpus_roots()
    subagent = sum(1 for _l, _b, files in rows for p in files if is_subagent_path(p))
    total = sum(len(files) for _l, _b, files in rows)
    return {
        "roots": [{"label": lbl, "path": base, "files": len(files)}
                  for lbl, base, files in rows],
        "total": total,
        "subagent_transcripts": subagent,
        "operator_bearing": total - subagent,
        "dedup": "by filename; precedence live > archive > rescued",
    }


# ---------------------------------------------------------------- schema
def _connect(db_path: Optional[Path]) -> sqlite3.Connection:
    p = Path(db_path) if db_path else _DEFAULT_DB
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)")
    row = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    have = int(row[0]) if row else 0
    con.execute("""CREATE TABLE IF NOT EXISTS events(
        event_id TEXT PRIMARY KEY, session TEXT NOT NULL, line INTEGER NOT NULL,
        ts REAL, voice TEXT NOT NULL, type TEXT NOT NULL, text TEXT NOT NULL,
        cwd TEXT, branch TEXT, tokens INTEGER, uuid TEXT, parent_uuid TEXT,
        indexed_at REAL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS ingest_state(
        path TEXT PRIMARY KEY, mtime REAL, lines INTEGER)""")
    con.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
        USING fts5(text, event_id UNINDEXED)""")
    # The RAW parent chain, for every record carrying a uuid -- INCLUDING records that
    # produce no event (tool calls, tool results, thinking blocks). Without it 93.8% of
    # parent links dangle: a child's parent is usually a record the indexer skipped for
    # having no text, so the walk dead-ends one hop out. Measured on the live corpus
    # before this table existed: 14,983 parent links, 927 resolving.
    con.execute("""CREATE TABLE IF NOT EXISTS chain(
        session TEXT NOT NULL, uuid TEXT NOT NULL, parent_uuid TEXT,
        PRIMARY KEY(session, uuid))""")
    if have < _SCHEMA_VERSION:
        cols = {r[1] for r in con.execute("PRAGMA table_info(events)")}
        for col in ("uuid", "parent_uuid"):
            if col not in cols:
                con.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT")
        if "is_subagent" not in cols:
            # 2026-08-16 authorship fix (RED a5afd360). Whose transcript this row came
            # from, stamped from the source PATH at
            # ingest. NULL means "arrived before this column existed AND its source has
            # since rotated away" -- unevaluable, not false. Readers COALESCE it to 0 (see
            # directives._operator_utterances): including an unknown row risks a little
            # contamination, dropping it risks losing his voice from the twenty rescued
            # sessions that exist nowhere else, and this organ exists to stop exactly that.
            con.execute("ALTER TABLE events ADD COLUMN is_subagent INTEGER")
        if "indexed_at" not in cols:
            # known_at, in the grammar's sense (sec 1): WHEN THIS BECAME KNOWABLE, which is
            # not when it happened. A transcript written last week and ingested today is new
            # to every reader today, and the ambient delta is a knowability question.
            # Existing rows stay NULL and that NULL is not a guess -- it means "arrived
            # before this column existed", which is before every mark that can now be taken.
            con.execute("ALTER TABLE events ADD COLUMN indexed_at REAL")
        # Derived tables only -- rebuilt from `events`, never a source of truth.
        con.execute("DROP TABLE IF EXISTS pyramid")
        con.execute("DROP TABLE IF EXISTS edges")
        # Re-read every file still on disk so the added columns fill in. Rows whose source
        # has rotated away keep their NULLs and keep their place in the archive.
        con.execute("DELETE FROM ingest_state")
    con.execute("INSERT OR REPLACE INTO meta VALUES('schema_version', ?)",
                (str(_SCHEMA_VERSION),))
    con.commit()
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
            # The harness's own causal chain. Present on user/assistant/system/attachment
            # records and ABSENT on every queue-operation record (measured: 0/398) -- which
            # is where his queued voice lives, so S4 must bridge rather than assume.
            "uuid": str(obj.get("uuid") or "") or None,
            "parent_uuid": str(obj.get("parentUuid") or "") or None,
            "tokens": max(1, len(text) // 4)}


# ---------------------------------------------------------------- ingest
def ingest(paths: Optional[List[Path]] = None,
           db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Index the manifest incrementally. The report IS the coverage contract."""
    manifest = [Path(p) for p in (paths if paths is not None else default_corpus())]
    con = _connect(db_path)
    files_indexed, files_failed = 0, []
    events_new = lines_unparsed = events_backfilled = 0
    # One known_at for the whole run: every event this pass makes knowable became knowable
    # together, and a per-row clock would let a long ingest straddle a reader's mark.
    run_started = time.time()
    try:
        for f in manifest:
            try:
                st = f.stat()
                session = f.stem
                # authorship fix a5afd360: the flag is a property of the SOURCE PATH, not
                # of any record, so it
                # is stamped for every file in the manifest -- BEFORE the unchanged-skip
                # below, whose rows are exactly the ones that predate the column and would
                # otherwise never be reached again.
                sub_flag = 1 if is_subagent_path(f) else 0
                con.execute(
                    "UPDATE events SET is_subagent=? WHERE session=? AND is_subagent IS NULL",
                    (sub_flag, session))
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
                        # The raw chain is recorded for EVERY record with a uuid, before
                        # the text filter -- a tool call carries no text and no meaning of
                        # its own, but it is a real link in the causal chain, and dropping
                        # it is what left 93.8% of parent pointers dangling.
                        if obj.get("uuid"):
                            con.execute(
                                "INSERT OR REPLACE INTO chain(session, uuid, parent_uuid) "
                                "VALUES(?,?,?)",
                                (session, str(obj["uuid"]),
                                 str(obj.get("parentUuid") or "") or None))
                        ev = _event_from(obj)
                        if ev is None:
                            continue
                        eid = f"{session}:{n_line}"
                        got = con.execute(
                            "INSERT OR IGNORE INTO events(event_id, session, line, ts, "
                            "voice, type, text, cwd, branch, tokens, uuid, parent_uuid, "
                            "indexed_at, is_subagent) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (eid, session, n_line, ev["ts"], ev["voice"], ev["type"],
                             ev["text"], ev["cwd"], ev["branch"], ev["tokens"],
                             ev["uuid"], ev["parent_uuid"], run_started, sub_flag))
                        if got.rowcount:
                            con.execute(
                                "INSERT INTO events_fts(text, event_id) VALUES(?,?)",
                                (ev["text"], eid))
                            events_new += 1
                        else:
                            # The row predates a schema that added columns. Backfill in
                            # place -- the alternative (drop and re-ingest) destroys rows
                            # whose source file has since rotated away, which is exactly
                            # how this organ lost >=219 events on 2026-08-11.
                            fixed = con.execute(
                                "UPDATE events SET uuid=?, parent_uuid=? "
                                "WHERE event_id=? AND uuid IS NULL",
                                (ev["uuid"], ev["parent_uuid"], eid))
                            events_backfilled += fixed.rowcount or 0
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
            "events_new": events_new, "events_backfilled": events_backfilled,
            "lines_unparsed": lines_unparsed,
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

    THE AXIS COUNTS UTTERANCES, NOT RECORDS (S4 fix, 2026-08-11). The harness records one
    operator turn several times over -- the queue-operation enqueue and dequeue, plus the
    delivered `user` twin, identical text seconds apart -- so counting rows double-counts
    his voice, and it double-counts it across the verdict threshold: the live "fan out /
    don't get bogged down in the mechanics" family read 4 operator events across 2 sessions
    (STANDING-DIRECTIVE) when he had in fact said it twice, once per session (RECURRING).
    `operator_records` keeps the raw number visible -- the correction is labelled, not
    hidden -- and `utterance_key` holds the collapsing law for every consumer.

    The repetition-counts note (2026-08-01) was hand-made because nothing measured this;
    this verb retires that class of hand-count. No LLM anywhere in the path."""
    con = _connect(db_path)
    try:
        seen: Dict[str, Dict[str, Any]] = {}
        for pat in patterns:
            phrase = '"' + str(pat).replace('"', " ") + '"'
            rows = con.execute(
                "SELECT e.event_id, e.session, e.line, e.ts, e.voice, e.text "
                "FROM events_fts JOIN events e ON e.event_id = events_fts.event_id "
                "WHERE events_fts MATCH ?", (phrase,)).fetchall()
            for r in rows:
                seen[r[0]] = {"event_id": r[0], "session": r[1], "line": r[2],
                              "ts": r[3], "voice": r[4], "text": r[5]}
    finally:
        con.close()

    events = sorted(seen.values(), key=lambda e: (e["ts"] or 0, e["event_id"]))
    op_records = [e for e in events if e["voice"] == "operator"]
    # Collapse to distinct utterances, keeping the FIRST record of each -- the earliest
    # record is when he actually said it, so spans stay honest.
    ops, _utt_seen = [], set()
    for e in op_records:
        k = utterance_key(e["session"], e["text"])
        if k in _utt_seen:
            continue
        _utt_seen.add(k)
        ops.append(e)
    by_voice: Dict[str, int] = {}
    for e in events:
        by_voice[e["voice"]] = by_voice.get(e["voice"], 0) + 1
    op_sessions = sorted({e["session"] for e in ops})

    _op_ids = {e["event_id"] for e in ops}
    per_session: List[Dict[str, Any]] = []
    for s in sorted({e["session"] for e in events}):
        evs = [e for e in events if e["session"] == s]
        per_session.append({
            "session": s, "events": len(evs),
            "operator_events": sum(1 for e in evs if e["event_id"] in _op_ids),
            "operator_records": sum(1 for e in evs if e["voice"] == "operator"),
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
            "operator_events": n_op, "operator_records": len(op_records),
            "sessions": n_sess, "by_voice": by_voice,
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
