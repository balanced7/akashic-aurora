"""arsenal.media.catalog -- every recording the house has seen, what it is and what was learned about it, in one
SQLite file; and the two ways a file gets in (a drop on the editor, a drop on media-import.cmd).

Why it exists: there was no index of recordings, so the editor's library, the agents and the coaching runs each
re-read 2.4 GB files to learn their length, tracks and date. Now probe() writes a sidecar once and the catalog
indexes it; everyone asks the catalog.

The truth is the sidecars (<state>/sidecars/<id>.json, written by probe.py). Every write here goes to the sidecar
first and then re-indexes that one file, so catalog.sqlite is always a function of the sidecars: rebuild() drops it
and reproduces it row for row. SQLite in WAL mode (readers never wait for the writer), one connection per call.

    ingest(path_or_dir, proxy=False, shots=False, peaks=False)   # the editor's quick import: probe + sidecar + row
    resolve_dropped("2026-10-11 17-51-11.mp4", 2440506138, 1791758719000)   # a browser drop -> the real path
    find(kind="screen", n_audio=1, recorded_after="2026-10-10")
    link(media_id)          # practice sessions and Riot matches that overlap it in wall time

A browser drop hands the page a File (name, size, lastModified), never a path; copying 2.4 GB to the server is what
resolve_dropped() avoids. It looks in the catalog, then in the library roots (arsenal serve's DEFAULT_ROOTS, the
roots passed in, and every folder the catalog already holds files from), two folder levels deep.

Measured 2026-10-12 on Daniel's 11 recordings of 2026-10-10/11 (under 1 s to 41 min, 8.5 GB): the quick ingest (probe +
sidecar + row + links) took 6.5 s cold, most of it the League kind check, and 0.18 s the second time with 0 new
rows. It found 3 live games, 4 replays, 3 piano takes (tied to practice session 20261011-165503-f62d348c) and 1
other screen recording. Riot matches are read from the league lane's cache only, which held none that night; with
NA1_5658447097's cached JSON copied into it, the 4 replays were tied to that match as replay candidates (5.3 s cold,
0.22 s again). resolve_dropped: 1 ms from the catalog, 1.9 ms from the library root on an empty catalog; find: 1 ms.
Two processes on one file for 15 s (a quick import loop against an add_spans loop): 144 imports, 1699 span writes,
0 errors, nothing lost; the review had seen 1 failure in each loop before reads and replaces retried.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import closing, contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence

from . import ff, probe as probe_mod

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Where the practice log keeps sessions (arsenal.performance.DEFAULT_ROOT); Riot matches: default_match_roots().
SESSIONS_ROOT = _REPO_ROOT / "state" / "arsenal" / "performance"

MEDIA_EXTS = frozenset((".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".flv", ".ts", ".m2ts", ".mts",
                        ".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a", ".aac"))
SPAN_KINDS = ("shot", "chapter", "clock_pass", "event", "window", "silence", "note")
DROP_MTIME_TOL_MS = 2000        # FAT/exFAT store mtimes to 2 s; NTFS and the browser agree to the millisecond
DROP_SCAN_DEPTH = 2             # root/name, root/x/name, root/x/y/name
REPLAY_LOOKBACK_S = 24 * 3600   # a replay recording is tied to the newest match that ended this long before it

SCHEMA = """
CREATE TABLE IF NOT EXISTS media (
  id TEXT PRIMARY KEY, path TEXT NOT NULL, name TEXT NOT NULL COLLATE NOCASE, size INTEGER, mtime_ns INTEGER,
  duration_s REAL, container TEXT, vcodec TEXT, w INTEGER, h INTEGER, fps REAL, vfr INTEGER, keyint_s REAL,
  n_audio INTEGER, encoder TEXT, recorded_at TEXT, recorded_epoch REAL, kind TEXT, probed_at TEXT, sidecar TEXT);
CREATE INDEX IF NOT EXISTS media_name_size ON media(name, size);
CREATE INDEX IF NOT EXISTS media_recorded ON media(recorded_at);
CREATE TABLE IF NOT EXISTS streams (media_id TEXT NOT NULL, idx INTEGER, kind TEXT, codec TEXT, channels INTEGER,
  sample_rate INTEGER, title TEXT, house_name TEXT);
CREATE INDEX IF NOT EXISTS streams_media ON streams(media_id);
CREATE TABLE IF NOT EXISTS tags (media_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT, source TEXT);
CREATE INDEX IF NOT EXISTS tags_media ON tags(media_id);
CREATE INDEX IF NOT EXISTS tags_key ON tags(key, value);
CREATE TABLE IF NOT EXISTS spans (media_id TEXT NOT NULL, kind TEXT NOT NULL, t0 REAL, t1 REAL, label TEXT,
  data_json TEXT, source TEXT);
CREATE INDEX IF NOT EXISTS spans_media ON spans(media_id, kind);
CREATE TABLE IF NOT EXISTS artifacts (media_id TEXT NOT NULL, kind TEXT NOT NULL, path TEXT NOT NULL,
  params_json TEXT, api TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS artifacts_media ON artifacts(media_id, kind);
"""
TABLES = ("media", "streams", "tags", "spans", "artifacts")
MEDIA_COLUMNS = ("id", "path", "name", "size", "mtime_ns", "duration_s", "container", "vcodec", "w", "h", "fps",
                 "vfr", "keyint_s", "n_audio", "encoder", "recorded_at", "recorded_epoch", "kind", "probed_at",
                 "sidecar")


# =================================================================================================
# connection
# =================================================================================================

def db_path() -> Path:
    return ff.state_dir() / "catalog.sqlite"


def connect(db: Optional[Path] = None) -> sqlite3.Connection:
    """A connection to the catalog (default <state>/catalog.sqlite), WAL mode, schema in place; rows as sqlite3.Row.
    One per call or thread: the editor's server is threaded and sqlite3 connections are not shared across threads."""
    path = Path(db) if db else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=10.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(SCHEMA)
    return con


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    with closing(connect()) as con:
        with con:                       # one transaction: commit on success, roll back on error
            yield con


# =================================================================================================
# sidecar -> rows (the only way rows are made, so rebuild() reproduces them exactly)
# =================================================================================================

def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _rows(sc: dict) -> Dict[str, List[tuple]]:
    v = sc.get("video") or {}
    media = (sc["id"], sc["path"], sc.get("name") or Path(sc["path"]).name, sc.get("size"), sc.get("mtime_ns"),
             sc.get("duration_s"), sc.get("container"), v.get("codec"), v.get("w"), v.get("h"), v.get("fps"),
             int(bool(v.get("vfr"))) if v else None, v.get("keyint_s"), len(sc.get("audio") or []),
             sc.get("encoder"), sc.get("recorded_at"), sc.get("recorded_epoch"), sc.get("kind"),
             sc.get("probed_at"), str(probe_mod.sidecar_path(sc["id"])))
    streams = []
    if v:
        streams.append((sc["id"], v.get("index"), "video", v.get("codec"), None, None, v.get("title"), None))
    for a in sc.get("audio") or []:
        streams.append((sc["id"], a.get("stream"), "audio", a.get("codec"), a.get("channels"), a.get("sample_rate"),
                        a.get("title"), a.get("house_name")))
    for s in sc.get("subtitles") or []:
        streams.append((sc["id"], s.get("stream"), "subtitle", s.get("codec"), None, None, s.get("title"), None))
    tags = [(sc["id"], t["key"], None if t.get("value") is None else str(t["value"]), t.get("source"))
            for t in sc.get("tags") or []]
    spans = [(sc["id"], "chapter", c.get("t0"), c.get("t1"), c.get("title"), None, "container")
             for c in sc.get("chapters") or []]
    spans += [(sc["id"], s["kind"], s.get("t0"), s.get("t1"), s.get("label"),
               None if s.get("data") is None else _json(s["data"]), s.get("source")) for s in sc.get("spans") or []]
    artifacts = [(sc["id"], a["kind"], a["path"], _json(a.get("params") or {}), a.get("api"), a.get("created_at"))
                 for a in sc.get("artifacts") or []]
    return {"media": [media], "streams": streams, "tags": tags, "spans": spans, "artifacts": artifacts}


def _index(con: sqlite3.Connection, sc: dict) -> Dict[str, int]:
    """Replace every row of one media id with the rows its sidecar implies."""
    counts = {}
    for table, rows in _rows(sc).items():
        key = "id" if table == "media" else "media_id"
        con.execute(f"DELETE FROM {table} WHERE {key} = ?", (sc["id"],))
        if rows:
            marks = ",".join("?" * len(rows[0]))
            con.executemany(f"INSERT INTO {table} VALUES ({marks})", rows)
        counts[table] = len(rows)
    return counts


def _load(media_id: str) -> dict:
    sc = probe_mod.read_sidecar(media_id)
    if sc is None:
        raise ff.MediaError(f"media {media_id} has no sidecar: probe or import the file first")
    return sc


def _mutate(media_id: str, change) -> dict:
    """Sidecar first, then its rows: the database never holds what the sidecars do not. Adding knowledge about a
    probed file imports it."""
    with probe_mod.sidecar_lock(media_id):
        sc = _load(media_id)
        change(sc)
        sc["cataloged"] = True
        probe_mod.write_sidecar(sc)
        reindex(sc)             # under the lock: rows land in the order the sidecars were written
    return sc


def reindex(sidecar: dict) -> None:
    """Rewrite one file's rows from its sidecar (probe() calls this when it re-reads a cataloged file)."""
    with _db() as con:
        _index(con, sidecar)


# =================================================================================================
# writes
# =================================================================================================

def is_cataloged(media_id: str) -> bool:
    return bool((probe_mod.read_sidecar(media_id) or {}).get("cataloged"))


def _merged(given: dict, fresh: Optional[dict]) -> dict:
    """What upsert writes. The sidecar on disk is the truth for what was learned (spans, artifacts, tags, links,
    kind), so a probe result held while another writer added knowledge cannot erase it. The file's facts come from
    the newer probe; on a tie the disk's, which keeps a keyframe index added since."""
    if fresh is None:
        return dict(given)
    if (fresh.get("probed_at") or "") >= (given.get("probed_at") or ""):
        return dict(fresh)
    out = dict(given)
    out.update({k: fresh[k] for k in probe_mod._KEPT_ON_REFRESH if k in fresh})
    return out


def upsert(sidecar: dict) -> str:
    """Import one probed file: mark its sidecar cataloged and index it (a probe() result or the sidecar dict).
    Re-upserting the same sidecar changes nothing: rows are replaced, never added. It brings facts, never
    knowledge: what the sidecar on disk learned since (spans, tags ...) is kept; add_spans, tag and add_artifact
    change knowledge."""
    sc = probe_mod.pure(sidecar)
    if sc.get("schema") != probe_mod.SIDECAR_SCHEMA or not sc.get("id"):
        raise ff.MediaError("upsert wants an arsenal.media.sidecar/v0 dict (from probe.probe)")
    with probe_mod.sidecar_lock(sc["id"]):
        fresh = probe_mod.read_sidecar(sc["id"])
        sc = _merged(sc, fresh)
        sc["cataloged"] = True
        if fresh != json.loads(_json(sc)):
            probe_mod.write_sidecar(sc)
        reindex(sc)
    return sc["id"]


def _span_row(row, kind: str, source: str) -> dict:
    if isinstance(row, dict):
        t0 = row.get("t0", row.get("start", row.get("t")))
        t1 = row.get("t1", row.get("end", t0))
        label, data = row.get("label"), row.get("data")
    elif isinstance(row, (int, float)):
        t0 = t1 = row
        label = data = None
    else:
        seq = list(row) + [None, None, None]
        t0, t1, label, data = seq[0], seq[1] if seq[1] is not None else seq[0], seq[2], seq[3]
    if t0 is None:
        raise ff.MediaError(f"a {kind} span needs a start time: {row!r}")
    if t1 is not None and float(t1) < float(t0):
        raise ff.MediaError(f"a {kind} span ends before it starts: {row!r}")
    return {"kind": kind, "t0": float(t0), "t1": None if t1 is None else float(t1),
            "label": None if label is None else str(label), "data": data, "source": source}


def add_spans(media_id: str, kind: str, rows: Iterable, *, source: str) -> int:
    """Time-ranged metadata for one file: rows are {t0, t1, label, data} dicts, (t0, t1[, label[, data]]) tuples, or
    single times (points). A second call with the same (kind, source) REPLACES that producer's rows, so re-running a
    detector never duplicates them. Returns how many rows were stored."""
    if kind not in SPAN_KINDS:
        raise ff.MediaError(f"span kind {kind!r} is not one of {', '.join(SPAN_KINDS)}")
    new = [_span_row(r, kind, source) for r in rows]

    def change(sc: dict) -> None:
        sc["spans"] = [s for s in sc.get("spans") or [] if (s["kind"], s.get("source")) != (kind, source)] + new
    _mutate(media_id, change)
    return len(new)


def add_artifact(media_id: str, kind: str, path, *, params: dict, api: str) -> None:
    """Remember a file made from this media (proxy, peaks, words, sheet, clockmap, stems). The same path again
    replaces its row."""
    entry = {"kind": kind, "path": str(Path(path).resolve()), "params": dict(params or {}), "api": api,
             "created_at": datetime.now().isoformat(timespec="seconds")}

    def change(sc: dict) -> None:
        sc["artifacts"] = [a for a in sc.get("artifacts") or [] if a["path"] != entry["path"]] + [entry]
    _mutate(media_id, change)


def artifact(media_id: str, kind: str, *, params: Optional[dict] = None) -> Optional[dict]:
    """The newest artifact of that kind (and those params, when given) whose file still exists."""
    sc = probe_mod.read_sidecar(media_id) or {}
    want = None if params is None else _json(params)
    hits = [a for a in sc.get("artifacts") or [] if a["kind"] == kind and os.path.isfile(a["path"])
            and (want is None or _json(a.get("params") or {}) == want)]
    return max(hits, key=lambda a: a.get("created_at") or "") if hits else None


def tag(media_id: str, key: str, value, *, source: str = "user") -> None:
    """Set a tag (match_id, champion, practice_session, replay=true ...). value may be a list (one row each);
    a second call with the same (key, source) replaces it; value None removes it."""
    values = value if isinstance(value, (list, tuple)) else ([] if value is None else [value])

    def change(sc: dict) -> None:
        kept = [t for t in sc.get("tags") or [] if (t["key"], t.get("source")) != (key, source)]
        sc["tags"] = kept + [{"key": key, "value": str(v), "source": source} for v in values]
    _mutate(media_id, change)


def rebuild() -> dict:
    """Drop the database and re-index every cataloged sidecar: the sidecars are the truth, the database is an
    index. (Sidecars of files that were only probed, never imported, stay out, as they were.)"""
    from . import receipt
    t0 = time.perf_counter()
    paths = sorted(probe_mod.sidecar_dir().glob("*.json")) if probe_mod.sidecar_dir().is_dir() else []
    errors, counts, n_cat = [], {t: 0 for t in TABLES}, 0
    with _db() as con:
        for table in TABLES:
            con.execute(f"DELETE FROM {table}")
        for p in paths:
            try:
                sc = json.loads(probe_mod.retry_shared(lambda: p.read_text(encoding="utf-8")))
                if not sc.get("cataloged"):
                    continue
                n_cat += 1
                for table, n in _index(con, sc).items():
                    counts[table] += n
            except (OSError, ValueError, KeyError) as exc:
                errors.append(f"{p.name}: {exc}")
    payload = {"sidecars": len(paths), "cataloged": n_cat, "rows": counts, "errors": errors, "db": str(db_path()),
               "seconds": round(time.perf_counter() - t0, 3)}
    return receipt.result("find", None, {"op": "rebuild"}, payload,
                          ["a sidecar that is not valid JSON is skipped and named in errors"])


def dump() -> Dict[str, List[tuple]]:
    """Every row of every table, sorted: two catalogs are the same when their dumps are equal."""
    with closing(connect()) as con:
        return {t: sorted((tuple(r) for r in con.execute(f"SELECT * FROM {t}")), key=repr) for t in TABLES}


# =================================================================================================
# reads
# =================================================================================================

def _wall_time(value) -> str:
    """A recorded_after / recorded_before bound in the stored form, 'YYYY-MM-DDTHH:MM:SS' local wall time, so text
    order is time order: '2026-10-11 17:00' and '2026-10-11T17:00' are the same bound (as text the space sorts
    before every 'T' of that day), and so are a datetime or a date. An aware time is moved into this machine's zone
    first; anything that is not an ISO date or time refuses rather than comparing as text."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    else:
        try:
            dt = datetime.fromisoformat(str(value).strip())
        except ValueError:
            raise ff.MediaError(f"find: {value!r} is not an ISO date or time "
                                "(YYYY-MM-DD[ HH:MM[:SS]], local)") from None
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt.isoformat()


_FIND_SPECIAL = {"recorded_after": ("recorded_at >= ?", _wall_time), "recorded_before": ("recorded_at < ?", _wall_time),
                 "duration_min": ("duration_s >= ?", float), "duration_max": ("duration_s <= ?", float),
                 "text": ("(name LIKE ? OR path LIKE ?)", None)}


def find(**where) -> List[dict]:
    """Media rows matching every condition, newest recording first.

    Any media column matches exactly (kind="screen", n_audio=1, vcodec="hevc", name=...). Also: recorded_after /
    recorded_before (local wall time: an ISO date or time with a space or a T, a datetime or a date), duration_min /
    duration_max (s), text (a substring of the name or path), tag ("key=value", or a (key, value) pair),
    has_artifact ("proxy"), limit. An unknown key refuses rather than matching everything."""
    clauses, args = [], []
    limit = where.pop("limit", None)
    for key, value in where.items():
        if value is None:
            continue
        if key in MEDIA_COLUMNS:
            clauses.append(f"{key} = ?")
            args.append(int(value) if isinstance(value, bool) else value)
        elif key in _FIND_SPECIAL:
            sql, cast = _FIND_SPECIAL[key]
            clauses.append(sql)
            args += [f"%{value}%", f"%{value}%"] if cast is None else [cast(value)]
        elif key == "tag":
            k, _, v = value.partition("=") if isinstance(value, str) else (value[0], "=", value[1])
            clauses.append("id IN (SELECT media_id FROM tags WHERE key = ? AND value = ?)")
            args += [k, str(v)]
        elif key == "has_artifact":
            clauses.append("id IN (SELECT media_id FROM artifacts WHERE kind = ?)")
            args.append(value)
        else:
            raise ff.MediaError(f"find: unknown condition {key!r} (columns: {', '.join(MEDIA_COLUMNS)}; also "
                                f"{', '.join(_FIND_SPECIAL)}, tag, has_artifact, limit)")
    sql = "SELECT * FROM media" + (" WHERE " + " AND ".join(clauses) if clauses else "")
    sql += " ORDER BY recorded_at DESC, name"
    if limit:
        sql += f" LIMIT {int(limit)}"
    with closing(connect()) as con:
        return [dict(r) for r in con.execute(sql, args)]


def spans(media_id: str, kind: Optional[str] = None) -> List[dict]:
    """Time-ranged rows of one file (all kinds, or one), in time order."""
    sql = "SELECT kind, t0, t1, label, data_json, source FROM spans WHERE media_id = ?"
    args: list = [media_id]
    if kind:
        sql += " AND kind = ?"
        args.append(kind)
    with closing(connect()) as con:
        rows = [dict(r) for r in con.execute(sql + " ORDER BY t0, kind", args)]
    for r in rows:
        r["data"] = json.loads(r.pop("data_json")) if r.get("data_json") else None
    return rows


# =================================================================================================
# drag and drop: a browser File (name, size, lastModified) -> the real path
# =================================================================================================

def _serve_roots() -> List[Path]:
    """arsenal serve's library roots (imported lazily: 77 ms once, then free)."""
    try:
        from arsenal.serve import DEFAULT_ROOTS
    except Exception:
        return []
    return [Path(r) for r in DEFAULT_ROOTS]


def library_roots(extra: Optional[Sequence] = None) -> List[Path]:
    """Roots a dropped file is looked for in: the ones passed in, arsenal serve's, and every folder the catalog
    already holds a file from (import one file from a folder and the folder becomes a root)."""
    roots: List[Path] = [Path(r) for r in (extra or [])] + _serve_roots()
    try:
        with closing(connect()) as con:
            roots += [Path(r[0]).parent for r in con.execute("SELECT path FROM media")]
    except sqlite3.Error:
        pass
    seen, out = set(), []
    for r in roots:
        key = os.path.normcase(str(r))
        if key not in seen and r.is_dir():
            seen.add(key)
            out.append(r)
    return out


def _matches(path: str, size: int, last_modified_ms: int) -> Optional[float]:
    """|mtime difference| in ms when the file at path has this size and an mtime within tolerance, else None.
    last_modified_ms <= 0 means the caller does not know it: name and size decide alone (difference 0)."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    if st.st_size != size:
        return None
    if last_modified_ms <= 0:
        return 0.0
    diff = abs(st.st_mtime_ns / 1e6 - last_modified_ms)
    return diff if diff <= DROP_MTIME_TOL_MS else None


def _scan(root: Path, name: str, depth: int) -> Iterator[str]:
    """Paths named `name` under root, at most `depth` folders down (names compared without a stat)."""
    folded = os.path.normcase(name)
    stack = [(str(root), 0)]
    while stack:
        folder, level = stack.pop()
        try:
            with os.scandir(folder) as it:
                for entry in it:
                    if os.path.normcase(entry.name) == folded:
                        yield entry.path
                    elif level < depth and entry.is_dir(follow_symlinks=False):
                        stack.append((entry.path, level + 1))
        except OSError:
            continue


def resolve_dropped(name: str, size: int, last_modified_ms: int, *, roots: Optional[Sequence] = None) -> Optional[str]:
    """The real path of a file dropped on the editor, from what the browser knows (File.name, .size,
    .lastModified); None when no library root holds it (the editor then names the folder to add as a root).

    Matches name + exact size + mtime within 2 s (a lastModified of 0, "unknown", leaves name and size to decide):
    the catalog first, then the library roots. Never copies."""
    name = Path(str(name).replace("\\", "/")).name
    best: Optional[tuple] = None
    with closing(connect()) as con:
        for row in con.execute("SELECT path FROM media WHERE name = ? AND size = ?", (name, int(size))):
            diff = _matches(row[0], int(size), int(last_modified_ms))
            if diff is not None and (best is None or diff < best[0]):
                best = (diff, row[0])
    if best:
        return str(Path(best[1]))
    for root in library_roots(roots):
        direct = root / name
        diff = _matches(str(direct), int(size), int(last_modified_ms))
        if diff is not None:
            return str(direct)
        for hit in _scan(root, name, DROP_SCAN_DEPTH):
            diff = _matches(hit, int(size), int(last_modified_ms))
            if diff is not None and (best is None or diff < best[0]):
                best = (diff, hit)
        if best:
            return str(Path(best[1]))
    return None


# =================================================================================================
# link: what happened at the same wall time (practice sessions, Riot matches)
# =================================================================================================

def _iso_epoch(text) -> Optional[float]:
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def _sessions(root: Path, t0: float, t1: float) -> List[dict]:
    """Practice sessions whose [opened, opened + duration] can overlap [t0, t1]. Session folders are named by their
    LOCAL opening time (YYYYMMDD-HHMMSS-...), so only folders opened in the 24 h before t1 are read."""
    if not root.is_dir():
        return []
    lo = datetime.fromtimestamp(t0 - 24 * 3600).strftime("%Y%m%d-%H%M%S")
    hi = datetime.fromtimestamp(t1 + 60).strftime("%Y%m%d-%H%M%S")
    out = []
    for entry in sorted(os.listdir(root)):
        if not (lo <= entry[:15] <= hi):
            continue
        try:
            meta = json.loads((root / entry / "session.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        start = meta["opened_ns"] / 1e9 if meta.get("opened_ns") else _iso_epoch(meta.get("opened_at"))
        if start is None:
            continue
        dur = meta.get("duration_s")
        if dur is None and meta.get("last_t_ms") is not None:
            dur = meta["last_t_ms"] / 1000.0
        out.append({"session": meta.get("session") or entry, "start": start, "end": start + float(dur or 0.0),
                    "closed": bool(meta.get("closed")), "events": meta.get("event_count")})
    return out


_match_cache: Dict[str, tuple] = {}


def default_match_roots() -> List[Path]:
    """Where cached Riot matches are looked for: the league lane's cache (arsenal.media.league.riot.default_root(),
    <state>/league/matches, so ARSENAL_MEDIA_STATE moves it too)."""
    try:
        from .league import riot
    except Exception:                  # the league lane is not importable: nothing cached to link to
        return []
    return [riot.default_root()]


def _matches_in(roots: Sequence[Path]) -> List[dict]:
    """Riot match windows from cached match files (match-v5 shape), read once per file version: the riot cache's
    layouts <id>/match.json and <id>.match.json, and a folder holding one match.json."""
    out = []
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        found = (set(root.glob("match.json")) | set(root.glob("*.match.json")) | set(root.glob("*/match.json"))
                 | set(root.glob("*/*/match.json")))
        for p in sorted(found):
            st = p.stat()
            key = str(p)
            if _match_cache.get(key, (None,))[0] != (st.st_size, st.st_mtime_ns):
                try:
                    m = json.loads(p.read_text(encoding="utf-8"))
                    info = m.get("info") or {}
                    start = (info.get("gameStartTimestamp") or info.get("gameCreation") or 0) / 1000.0
                    end = (info.get("gameEndTimestamp") or 0) / 1000.0 or start + float(info.get("gameDuration") or 0)
                    row = {"match_id": (m.get("metadata") or {}).get("matchId"), "start": start, "end": end,
                           "path": str(p)}
                except (OSError, ValueError, TypeError):
                    row = None
                _match_cache[key] = ((st.st_size, st.st_mtime_ns), row)
            if _match_cache[key][1] and _match_cache[key][1]["start"] > 0:
                out.append(dict(_match_cache[key][1]))
    return out


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def link(media_id: str, *, sessions_root=None, match_roots: Optional[Sequence] = None,
         write_receipt: bool = True) -> dict:
    """Tie a recording to what happened at the same wall time, store the links in its sidecar and tags, and return
    them: practice sessions (confidence = the share of the recording inside the session) and Riot matches played
    during it; a league_replay recording also gets the newest match that ended in the 24 h before it, as a
    replay candidate (confidence 0.5: recency only, the clock map confirms it). A recording that overlaps a
    practice session and is not League footage becomes kind "piano"."""
    from . import receipt
    if os.path.isfile(str(media_id)):
        media_id = probe_mod.probe(media_id)["id"]
    sc = _load(media_id)
    t0 = sc.get("recorded_epoch")
    if t0 is None:
        raise ff.MediaError(f"{sc.get('name')}: no recorded time, so nothing can be linked by time")
    dur = float(sc.get("duration_s") or 0.0)
    t1 = t0 + dur
    practice = []
    for s in _sessions(Path(sessions_root) if sessions_root else SESSIONS_ROOT, t0, t1):
        ov = _overlap(t0, t1, s["start"], s["end"])
        if ov > 0 or (dur == 0 and s["start"] <= t0 <= s["end"]):
            practice.append({"session": s["session"], "overlap_s": round(ov, 3),
                             "confidence": round(ov / dur, 3) if dur else 1.0,
                             "session_start": datetime.fromtimestamp(s["start"]).isoformat(timespec="seconds"),
                             "session_s": round(s["end"] - s["start"], 3), "events": s["events"]})
    matches = []
    roots = [Path(r) for r in (match_roots if match_roots is not None else default_match_roots())]
    windows = _matches_in(roots)
    for m in windows:
        ov = _overlap(t0, t1, m["start"], m["end"])
        if ov > 0:
            matches.append({"match_id": m["match_id"], "relation": "played_during", "overlap_s": round(ov, 3),
                            "confidence": round(ov / min(dur or ov, m["end"] - m["start"]), 3)})
    if sc.get("kind") == "league_replay" and not matches:
        before = [m for m in windows if 0 <= t0 - m["end"] <= REPLAY_LOOKBACK_S]
        if before:
            m = max(before, key=lambda x: x["end"])
            matches.append({"match_id": m["match_id"], "relation": "replay_candidate",
                            "gap_s": round(t0 - m["end"], 1), "confidence": 0.5})
    practice.sort(key=lambda x: -x["confidence"])
    links = {"practice_sessions": practice, "riot_matches": matches,
             "recorded": {"start": sc.get("recorded_at"), "from": sc.get("recorded_from"), "duration_s": dur}}

    def change(s: dict) -> None:
        s["links"] = links
        s["tags"] = [t for t in s.get("tags") or [] if t.get("source") != "link"]
        s["tags"] += [{"key": "practice_session", "value": p["session"], "source": "link"} for p in practice]
        s["tags"] += [{"key": "match_id", "value": m["match_id"], "source": "link"} for m in matches]
        if practice and practice[0]["confidence"] >= 0.5 and not str(s.get("kind", "")).startswith("league"):
            s["kind"], s["kind_from"] = "piano", "practice_overlap"
    sc = _mutate(media_id, change)
    src = {"path": sc["path"], "size": sc["size"], "mtime_ns": sc["mtime_ns"], "id": media_id}
    params = {"sessions_root": str(sessions_root or SESSIONS_ROOT),
              "match_roots": [str(r) for r in roots],
              "replay_lookback_s": REPLAY_LOOKBACK_S}
    return receipt.result("import", src, params, {"id": media_id, "kind": sc.get("kind"), "links": links},
                          ["wall times come from the OBS file name (local, 1 s) or the container's creation_time",
                           "a replay is tied to a match by recency only; Riot matches are read from cached JSON"],
                          write_receipt=write_receipt)


# =================================================================================================
# ingest: probe + sidecar + catalog row for every file first; the heavy artifacts after, each on request
# =================================================================================================

def _media_files(target: Path, recursive: bool) -> List[Path]:
    if target.is_file():
        return [target]
    if not target.is_dir():
        raise ff.MediaError(f"no such file or folder: {target}")
    walker = (Path(d) / f for d, _, fs in os.walk(target) for f in fs) if recursive else target.iterdir()
    return sorted(p for p in walker if p.is_file() and p.suffix.lower() in MEDIA_EXTS)


def _optional(module: str):
    """arsenal.media.<module> when another lane has built it, else None."""
    import importlib
    import importlib.util
    try:
        if importlib.util.find_spec(f"arsenal.media.{module}") is None:
            return None
        return importlib.import_module(f"arsenal.media.{module}")
    except Exception:
        return None


def _files_in(res) -> List[str]:
    """The existing files a primitive's result lists under "files" (a dict or a list of paths)."""
    files = (res or {}).get("files") if isinstance(res, dict) else None
    vals = files.values() if isinstance(files, dict) else (files or [])
    return sorted({str(x) for x in vals if isinstance(x, (str, Path)) and os.path.isfile(str(x))})


def _heavy(sc: dict, *, proxy: bool, shots: bool, peaks: bool, clock: str, done: list, skipped: dict,
           timings: dict) -> None:
    from . import api
    path, media_id = sc["path"], sc["id"]
    t = time.perf_counter()
    if sc.get("video"):
        probe_mod.probe(path, keyframes=True)          # re-indexes the row itself (the file is cataloged)
        done.append("keyframes")
        timings["keyframes_s"] = round(time.perf_counter() - t, 3)
    cmap = None
    want_clock = clock == "on" or (clock == "auto" and str(sc.get("kind", "")).startswith("league"))
    if want_clock:
        clock_mod = _optional("league.clock")
        if clock_mod is None or not hasattr(clock_mod, "clockmap"):
            skipped["clock"] = "arsenal.media.league.clock is not built yet"
        else:
            t = time.perf_counter()
            out = ff.state_dir() / "clockmap" / f"{media_id}.clockmap.json"
            try:                                       # another lane's reader: its failure is reported, not fatal
                cmap = clock_mod.clockmap(path, out=str(out))
            except Exception as exc:
                skipped["clock"] = f"failed: {type(exc).__name__}: {str(exc)[:200]}"
            if cmap is not None:
                if out.is_file():
                    add_artifact(media_id, "clockmap", out, params={"hud": "auto", "every": "keyframes"},
                                 api=api("clockmap"))
                passes = cmap.get("passes") or []
                add_spans(media_id, "clock_pass", [(p["file"][0], p["file"][1], p.get("id"),
                                                    {"speed": p.get("speed"), "offset": p.get("offset")})
                                                   for p in passes if p.get("file")], source="clock")
                done.append("clock")
                timings["clock_s"] = round(time.perf_counter() - t, 3)
    if (proxy or shots) and sc.get("video"):
        from . import shots as shots_mod
        t = time.perf_counter()
        shots_mod.proxy(path)
        done.append("proxy")
        timings["proxy_s"] = round(time.perf_counter() - t, 3)
        if shots:
            t = time.perf_counter()
            shots_mod.shots(path, clockmap=cmap)
            done.append("shots")
            timings["shots_s"] = round(time.perf_counter() - t, 3)
    if peaks and sc.get("audio"):
        peaks_mod = _optional("peaks")
        if peaks_mod is None or not hasattr(peaks_mod, "peaks"):
            skipped["peaks"] = "arsenal.media.peaks is not built yet"
        else:
            t = time.perf_counter()
            try:
                for a in sc["audio"]:
                    res = peaks_mod.peaks(path, track=a["index"])
                    for f in _files_in(res):
                        add_artifact(media_id, "peaks", f, params={"track": a["index"]}, api=api("peaks"))
                done.append("peaks")
                timings["peaks_s"] = round(time.perf_counter() - t, 3)
            except Exception as exc:                   # another lane's module: report, keep importing
                skipped["peaks"] = f"failed: {type(exc).__name__}: {str(exc)[:200]}"


def ingest(path_or_dir, *, recursive: bool = False, proxy: bool = True, shots: bool = True, peaks: bool = True,
           clock: str = "auto") -> List[dict]:
    """Import files into the catalog without copying or touching them; one house result per file.

    Two phases, so the cheap part lands first: (1) for EVERY file, probe + sidecar + catalog row + time links
    (~0.1-0.7 s a file, the editor's drop path); (2) then, per file and only when asked, the heavy artifacts: the
    full keyframe index, the 360p analysis proxy and its cuts (shots), waveform peaks per audio track, the League
    clock map. The editor's quick import is ingest(p, proxy=False, shots=False, peaks=False); running ingest again
    later with them on adds the artifacts (the probe is answered from the sidecar). clock: "auto" runs the clock map
    with the heavy phase for League footage, "on" whenever the League clock reader exists, "off" never. A file that
    fails reports its error and the others continue."""
    from . import receipt
    if clock not in ("auto", "on", "off"):
        raise ff.MediaError(f"clock must be auto, on or off, not {clock!r}")
    files = _media_files(Path(path_or_dir), recursive)
    params = {"recursive": recursive, "proxy": proxy, "shots": shots, "peaks": peaks, "clock": clock}
    blind = ["the originals are opened read-only and never copied",
             "kind is league_* only when arsenal.media.league.hud is built; peaks and clock need their lanes' modules"]
    staged = []
    for f in files:                                       # phase 1: every file becomes a catalog row
        t = time.perf_counter()
        entry = {"path": str(f), "done": [], "skipped": {}, "timings": {}}
        try:
            sc = probe_mod.probe(f)
            votes = sc.get("kind_votes")
            if sc.get("kind_from") == "rules" and probe_mod._hud() and (
                    votes is None or any(str(v).startswith("error") for v in votes)):
                sc = probe_mod.probe(f, refresh=True)     # the HUD reader was missing or failing then: ask again
            upsert(sc)
            entry["done"].append("probe")
            entry["timings"]["probe_s"] = round(time.perf_counter() - t, 3)
            if sc.get("recorded_epoch") is not None:
                link(sc["id"], write_receipt=False)
                entry["done"].append("link")
            entry["sc"] = probe_mod.read_sidecar(sc["id"])
        except (ff.MediaError, OSError) as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}" if isinstance(exc, OSError) else str(exc)
        staged.append(entry)
    heavy = proxy or shots or peaks or clock == "on"
    results = []
    for entry in staged:                                  # phase 2: the heavy artifacts, one file at a time
        sc = entry.pop("sc", None)
        if sc is not None and heavy:
            try:
                _heavy(sc, proxy=proxy, shots=shots, peaks=peaks, clock=clock, done=entry["done"],
                       skipped=entry["skipped"], timings=entry["timings"])
            except (ff.MediaError, OSError) as exc:
                entry["error"] = str(exc)
            sc = probe_mod.read_sidecar(sc["id"])
        payload = dict(entry)
        if sc is not None:
            payload.update({"id": sc["id"], "kind": sc.get("kind"), "recorded_at": sc.get("recorded_at"),
                            "duration_s": sc.get("duration_s"), "links": sc.get("links"),
                            "artifacts": [a["kind"] + ": " + a["path"] for a in sc.get("artifacts") or []],
                            "sidecar": str(probe_mod.sidecar_path(sc["id"]))})
            src = {"path": sc["path"], "size": sc["size"], "mtime_ns": sc["mtime_ns"], "id": sc["id"]}
        else:
            src = {"path": entry["path"]}
        results.append(receipt.result("import", src, params, payload, blind))
    return results


# =================================================================================================
# CLI: import and find
# =================================================================================================

def _print_rows(rows: List[dict]) -> None:
    for r in rows:
        dur = r.get("duration_s") or 0.0
        print(f"{r['id']}  {r.get('recorded_at') or '-':19s}  {dur / 60:6.1f} min  {r.get('kind') or '-':13s}  "
              f"{r.get('vcodec') or '-':5s} {r.get('w') or '-'}x{r.get('h') or '-'}  a:{r.get('n_audio')}  {r['path']}")
    print(f"({len(rows)} file{'s' if len(rows) != 1 else ''})")


def _cli_import(argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media import",
                                 description="import videos into the media catalog (probe + sidecar + catalog row, "
                                             "then proxy, scene cuts, waveform peaks), never copying or touching them")
    ap.add_argument("paths", nargs="+", help="files or folders")
    ap.add_argument("--recursive", action="store_true", help="also look inside sub-folders")
    ap.add_argument("--quick", action="store_true", help="probe + catalog row only (what the editor does on a drop)")
    ap.add_argument("--no-proxy", action="store_true")
    ap.add_argument("--no-shots", action="store_true")
    ap.add_argument("--no-peaks", action="store_true")
    ap.add_argument("--clock", choices=("auto", "on", "off"), default="auto")
    ap.add_argument("--dropped", action="store_true", help="(media-import.cmd) friendlier messages")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    quick = a.quick
    failed = 0
    for target in a.paths:
        try:
            results = ingest(target, recursive=a.recursive, proxy=not (quick or a.no_proxy),
                             shots=not (quick or a.no_shots), peaks=not (quick or a.no_peaks),
                             clock="off" if quick else a.clock)
        except ff.MediaError as exc:
            print(f"! {target}: {exc}")
            failed += 1
            continue
        if a.json:
            print(json.dumps(results, indent=1, default=str))
            continue
        if not results:
            print(f"{target}: no video or audio files here" + ("" if a.recursive else " (add --recursive?)"))
        for r in results:
            if r.get("error"):
                failed += 1
                print(f"! {Path(r['path']).name}: {r['error']}")
                continue
            sessions = [p["session"] for p in (r.get("links") or {}).get("practice_sessions", [])]
            matches = [m["match_id"] for m in (r.get("links") or {}).get("riot_matches", [])]
            print(f"{Path(r['path']).name}: {r.get('kind')}, {(r.get('duration_s') or 0) / 60:.1f} min, "
                  f"recorded {r.get('recorded_at')}; did {', '.join(r['done'])}"
                  + (f"; practice {', '.join(sessions)}" if sessions else "")
                  + (f"; match {', '.join(matches)}" if matches else "")
                  + "".join(f"; skipped {k} ({v})" for k, v in r["skipped"].items()))
    if a.dropped:
        print("The files stay where they are; the catalog only remembers them." if not failed
              else "Some files did not import. Read the messages above.")
    return 1 if failed else 0


def _cli_find(argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media find",
                                 description="query the media catalog: recordings by kind, date, track count; "
                                             "resolve a dropped file; link by time; rebuild from sidecars")
    ap.add_argument("--kind")
    ap.add_argument("--after", help="recorded at or after (YYYY-MM-DD[ HH:MM[:SS]], local; a T works too)")
    ap.add_argument("--before", help="recorded before (same form)")
    ap.add_argument("--n-audio", type=int)
    ap.add_argument("--text", help="a piece of the file name or path")
    ap.add_argument("--tag", help="key=value, e.g. practice_session=20261011-165503-f62d348c")
    ap.add_argument("--has-artifact", help="proxy, peaks, sheet, clockmap ...")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--resolve", nargs=3, metavar=("NAME", "SIZE", "LAST_MODIFIED_MS"),
                    help="where is the file a browser dropped (File.name, .size, .lastModified)?")
    ap.add_argument("--root", action="append", help="an extra library root for --resolve")
    ap.add_argument("--link", metavar="ID_OR_PATH", help="tie a recording to practice sessions and Riot matches")
    ap.add_argument("--spans", metavar="ID", help="time-ranged rows of one file (shots, chapters, clock passes)")
    ap.add_argument("--rebuild", action="store_true", help="rebuild catalog.sqlite from the sidecars")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.resolve:
        t = time.perf_counter()
        hit = resolve_dropped(a.resolve[0], int(a.resolve[1]), int(a.resolve[2]), roots=a.root)
        ms = (time.perf_counter() - t) * 1000
        print(json.dumps({"path": hit, "ms": round(ms, 1)}) if a.json else
              (f"{hit}  ({ms:.0f} ms)" if hit else f"not found in the catalog or the library roots ({ms:.0f} ms): "
               f"add its folder as a library root"))
        return 0 if hit else 1
    if a.link:
        res = link(a.link)
        print(json.dumps(res["links"], indent=1))
        return 0
    if a.spans:
        print(json.dumps(spans(a.spans), indent=1))
        return 0
    if a.rebuild:
        res = rebuild()
        print(json.dumps({k: res[k] for k in ("sidecars", "cataloged", "rows", "errors", "seconds", "db")}, indent=1))
        return 0
    rows = find(kind=a.kind, recorded_after=a.after, recorded_before=a.before, n_audio=a.n_audio, text=a.text,
                tag=a.tag, has_artifact=a.has_artifact, limit=a.limit)
    if a.json:
        print(json.dumps(rows, indent=1))
    else:
        _print_rows(rows)
    return 0


def cli(verb: str, argv: List[str]) -> int:
    return _cli_import(argv) if verb == "import" else _cli_find(argv)
