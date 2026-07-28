"""SqliteStore -- the durable Store backend with real cross-process safety.

WHY THIS EXISTS
---------------
FileStore serialises its WHOLE in-memory dict on every mutation and os.replace's it over
the shared path. Two processes each hold a full copy, so the second flush erases the first
writer's keys. Measured 2026-07-25 with an isolated 3-process probe: 450 writes attempted,
155 survived, 295 LOST -- 65.6% silent loss, no error raised, one worker's entire output
erased while it believed every write had succeeded.

Its cas() did not help: it compares against the same in-memory dict under a threading.RLock,
so it is blind across processes AND across instances (each FileStore builds its own lock).
A cross-process probe had every cas() return True, zero conflicts reported, and the child's
committed key gone.

Same probe against this class: 450 attempted, 450 survived, 0 lost.

WHY SQLITE AND NOT A LOCK AROUND THE OLD DESIGN
-----------------------------------------------
A lock alone is insufficient -- it guards the critical section while the compare still reads
stale in-memory state, so the section is correct-by-lock and wrong-by-data (kimi). The fix
has to make the compare read CURRENT state. SQLite does that natively: writes serialise, the
compare happens inside the engine, and there is no whole-file rewrite to clobber with.

Chosen over LMDB (zset scores are mutable, and maintaining score order in a key-sorted B-tree
needs a secondary index or a full scan -- "the zset encoding alone is a design project") and
over per-key files (fixes the hole but every list/set/zset mutation becomes a full-structure
rewrite). Both assessments are deepseek's, which priced its own per-key proposal and rejected
it. Full analysis: docs/filestore-coherence-design-2026-07.md,
research/reviewed/storage-engine-sweep-2026-07-26.md.

THE TWO RIDERS, both measured rather than assumed
-------------------------------------------------
1. CHECKPOINT POLICY IS MANDATORY, NOT OPTIONAL. Probed 2026-07-26: with one long-lived
   reader holding an open read transaction, the -wal file grew to 523,272 bytes and would
   not truncate; it fell to 0 only after the reader released AND an explicit
   wal_checkpoint(TRUNCATE) ran. Our runners and UI ARE long-lived readers, so this is our
   exact shape. See checkpoint() and wal_bytes() below -- the WAL size is a health signal,
   not something to discover as disk pressure.

2. BACKUP MUST NOT BE A FILE COPY. Copying the .db alone leaves the -wal behind and yields a
   stale-or-corrupt snapshot while still reporting success. Use backup_to(), which wraps
   sqlite3's online backup API. scripts/ops/snapshot_knowledge.py and
   scripts/harmonize_knowledge.py currently shutil.copy2 the store file and MUST be moved
   onto backup_to() in the same slice, or we trade a write-loss defect for a recovery-loss
   defect on the path memory records as "proven".

WHAT THIS CLASS DOES NOT PROTECT (kimi's ROT-2 -- a fix must name its own coverage)
----------------------------------------------------------------------------------
- Anything writing the .db file outside this class. deepseek's writer census found zero such
  paths for the JSON store; the same discipline must hold here.
- Multi-key atomicity ACROSS separate calls. Each method is atomic; a caller doing
  get-then-set across two calls still races. That is what cas() and update_atomic() are for.
- A reader that holds a transaction open indefinitely still starves the checkpoint. The
  policy mitigates; it does not make the hazard vanish.
"""
from __future__ import annotations

import fnmatch
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from core.foundation.store import Store

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hash (
    key   TEXT NOT NULL,
    field TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (key, field)
);
CREATE TABLE IF NOT EXISTS list (
    key   TEXT NOT NULL,
    idx   INTEGER NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (key, idx)
);
CREATE TABLE IF NOT EXISTS set_members (
    key    TEXT NOT NULL,
    member TEXT NOT NULL,
    PRIMARY KEY (key, member)
);
CREATE TABLE IF NOT EXISTS zset (
    key    TEXT NOT NULL,
    member TEXT NOT NULL,
    score  REAL NOT NULL,
    PRIMARY KEY (key, member)
);
-- The reason zset is a STRICT upgrade rather than a lateral move: this index covers
-- score-ordered range queries natively. FileStore sorts the whole set in memory on every
-- zrange. ORDER BY score, member also preserves Redis's lexicographic tie-break on equal
-- scores -- the exact semantic the W3 differential finding cost us.
CREATE INDEX IF NOT EXISTS zset_score ON zset (key, score, member);
CREATE TABLE IF NOT EXISTS expiry (
    key        TEXT PRIMARY KEY,
    expires_at REAL NOT NULL
);
"""

_DATA_TABLES = ("kv", "hash", "list", "set_members", "zset")


class SqliteStore(Store):
    """File-backed Store on SQLite in WAL mode. Safe across processes AND instances."""

    def __init__(self, path: Optional[str] = None, busy_timeout_ms: int = 10_000,
                 echo_json_path: Optional[str] = None):
        base = os.path.join(os.getenv("AI_SETUP", r"E:\AI-Setup"), "session_logs")
        os.makedirs(base, exist_ok=True)
        self._path = path or os.path.join(base, "store_state.db")
        # Migration-era rollback escrow (T118 D4): when set, close() exports the full
        # store to this JSON path in FileStore's on-disk format, so "select the file
        # backend again" finds every post-cutover write instead of a frozen twin. A
        # crash between closes leaves the echo stale -- that window is watched by
        # scripts/checkers/check_dual_authority.py, not wished away.
        self._echo_path = echo_json_path
        self._busy_timeout_ms = int(busy_timeout_ms)
        # Guards THIS object's connection handle. Cross-process safety comes from SQLite,
        # not from here -- unlike FileStore, where the RLock was mistaken for the guarantee.
        self._lock = threading.RLock()
        self._degraded: Optional[str] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    # ---------------------------------------------------------------- lifecycle
    def _connect(self) -> None:
        try:
            conn = sqlite3.connect(self._path, timeout=self._busy_timeout_ms / 1000.0,
                                   isolation_level=None, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(_SCHEMA)
            self._conn = conn
            self._degraded = None
        except Exception as e:
            # Mirrors FileStore's _degraded contract: refuse to persist rather than damage
            # what we could not read. A store that cannot open is loud, not silently empty.
            self._degraded = f"{type(e).__name__}: {e}"
            self._conn = None

    def is_available(self) -> bool:
        return self._conn is not None and self._degraded is None

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    if self._echo_path:
                        self._export_echo()
                    self.checkpoint()
                finally:
                    try:
                        self._conn.close()
                    except Exception:
                        pass
                    self._conn = None

    # ---------------------------------------------------- rider 1: WAL health
    def wal_bytes(self) -> int:
        """Size of the -wal sidecar. A health signal, not a curiosity: a long-lived reader
        prevents truncation and this grows without bound. Measured at 523,272 bytes with one
        held reader during the 2026-07-26 probe."""
        try:
            return os.path.getsize(self._path + "-wal")
        except OSError:
            return 0

    def checkpoint(self, mode: str = "TRUNCATE") -> bool:
        """Force a WAL checkpoint. Returns False when it could not fully complete -- which is
        the honest answer while a reader still holds a transaction open, not an error."""
        if self._conn is None:
            return False
        try:
            row = self._conn.execute(f"PRAGMA wal_checkpoint({mode})").fetchone()
            # row = (busy, log_pages, checkpointed_pages); busy=1 means blocked by a reader.
            return bool(row) and row[0] == 0
        except Exception:
            return False

    # ------------------------------------------------- rider 2: correct backup
    def backup_to(self, dest_path: str) -> bool:
        """Online, WAL-correct backup. Use this INSTEAD of copying the file.

        shutil.copy2 of a WAL database leaves the -wal behind and produces a stale or corrupt
        snapshot while still reporting success -- the failure mode that is worse than no
        backup, because it surfaces at restore time.
        """
        if self._conn is None:
            return False
        try:
            with sqlite3.connect(dest_path) as dest:
                self._conn.backup(dest)
            return True
        except Exception:
            return False

    # ------------------------------------------------- snapshot (reconciliation)
    def snapshot(self) -> Dict[str, Any]:
        """Point-in-time copy of every structure + expiry, in EXACTLY FileStore's
        snapshot shape -- HybridStore.reconcile() and the migration verifier consume
        this interchangeably with the FileStore one (T118 D6). Expired keys are swept
        first, matching FileStore's contract that a snapshot never resurrects."""
        with self._lock:
            if self._conn is None:
                return {"kv": {}, "hash": {}, "list": {}, "set": {},
                        "zset": {}, "expiry": {}}
            self.purge_expired()
            out: Dict[str, Any] = {"kv": {}, "hash": {}, "list": {}, "set": {},
                                   "zset": {}, "expiry": {}}
            for k, v in self._conn.execute("SELECT key,value FROM kv"):
                out["kv"][k] = v
            for k, f, v in self._conn.execute("SELECT key,field,value FROM hash"):
                out["hash"].setdefault(k, {})[f] = v
            for k, v in self._conn.execute("SELECT key,value FROM list ORDER BY key,idx"):
                out["list"].setdefault(k, []).append(v)
            for k, m in self._conn.execute("SELECT key,member FROM set_members"):
                out["set"].setdefault(k, []).append(m)
            for k, m, s in self._conn.execute("SELECT key,member,score FROM zset"):
                out["zset"].setdefault(k, {})[m] = float(s)
            for k, ts in self._conn.execute("SELECT key,expires_at FROM expiry"):
                out["expiry"][k] = float(ts)
            return out

    def _export_echo(self) -> None:
        """Write the whole store to the JSON twin in FileStore's on-disk format
        (buckets + __expiry__), atomically. Called from close() when echo_json_path
        is set. SQLite is cross-process-true, so any full export is coherent at a
        point in time and last-closer-wins is safe. Failure is LOUD, never raised:
        close() must still close, but the operator has to know the rollback escrow
        went stale."""
        import json as _json
        import logging
        try:
            snap = self.snapshot()
            payload = {"kv": snap["kv"], "hash": snap["hash"], "list": snap["list"],
                       "set": snap["set"], "zset": snap["zset"],
                       "__expiry__": snap["expiry"]}
            tmp = f"{self._echo_path}.tmp.{os.getpid()}"
            with open(tmp, "w", encoding="utf-8") as f:
                _json.dump(payload, f)
            last: Optional[Exception] = None
            for attempt in range(5):   # Windows: brief reader holds are contention
                try:
                    os.replace(tmp, self._echo_path)
                    return
                except OSError as e:
                    last = e
                    time.sleep(0.02 * (attempt + 1))
            raise last if last else OSError("replace failed")
        except Exception as e:
            logging.getLogger(__name__).error(
                f"SqliteStore echo export to {self._echo_path} FAILED ({e}) -- the "
                f"JSON rollback twin is STALE; a rollback now loses writes since the "
                f"last successful echo. check_dual_authority will flag the tear.")

    # ------------------------------------------------------------ expiry (TTL)
    def _now(self) -> float:
        return time.time()

    def _evict_if_expired(self, key: str) -> bool:
        """Lazy expiry, same contract as FileStore: a key past its TTL is dropped on touch."""
        if self._conn is None:
            return False
        row = self._conn.execute("SELECT expires_at FROM expiry WHERE key=?", (key,)).fetchone()
        if row and row[0] <= self._now():
            self._drop_key(key)
            return True
        return False

    def _drop_key(self, key: str) -> None:
        for t in _DATA_TABLES:
            self._conn.execute(f"DELETE FROM {t} WHERE key=?", (key,))
        self._conn.execute("DELETE FROM expiry WHERE key=?", (key,))

    def _raw_exists(self, key: str) -> bool:
        for t in _DATA_TABLES:
            if self._conn.execute(f"SELECT 1 FROM {t} WHERE key=? LIMIT 1", (key,)).fetchone():
                return True
        return False

    def purge_expired(self) -> int:
        """Sweep every key past its TTL. Lazy expiry alone never reclaims untouched keys, so
        without this the file grows monotonically."""
        with self._lock:
            if self._conn is None:
                return 0
            rows = self._conn.execute("SELECT key FROM expiry WHERE expires_at<=?",
                                      (self._now(),)).fetchall()
            for (k,) in rows:
                self._drop_key(k)
            return len(rows)

    # ------------------------------------------------------------------- kv
    def get(self, key: str) -> Optional[str]:
        with self._lock:
            if self._conn is None:
                return None
            self._evict_if_expired(key)
            row = self._conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
            return row[0] if row else None

    def set(self, key: str, value: str) -> bool:
        with self._lock:
            if self._conn is None:
                return False
            self._conn.execute("INSERT INTO kv(key,value) VALUES(?,?) "
                               "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                               (key, str(value)))
            self._conn.execute("DELETE FROM expiry WHERE key=?", (key,))
            return True

    def delete(self, *keys: str) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            n = 0
            for k in keys:
                if self._raw_exists(k):
                    n += 1
                self._drop_key(k)
            return n

    def exists(self, key: str) -> bool:
        with self._lock:
            if self._conn is None:
                return False
            self._evict_if_expired(key)
            return self._raw_exists(key)

    def setex(self, key: str, seconds: int, value: str) -> bool:
        with self._lock:
            if self._conn is None:
                return False
            self._conn.execute("INSERT INTO kv(key,value) VALUES(?,?) "
                               "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                               (key, str(value)))
            self._conn.execute("INSERT INTO expiry(key,expires_at) VALUES(?,?) "
                               "ON CONFLICT(key) DO UPDATE SET expires_at=excluded.expires_at",
                               (key, self._now() + int(seconds)))
            return True

    def expire(self, key: str, seconds: int) -> bool:
        with self._lock:
            if self._conn is None:
                return False
            if not self._raw_exists(key):
                return False
            self._conn.execute("INSERT INTO expiry(key,expires_at) VALUES(?,?) "
                               "ON CONFLICT(key) DO UPDATE SET expires_at=excluded.expires_at",
                               (key, self._now() + int(seconds)))
            return True

    def ttl(self, key: str) -> int:
        with self._lock:
            if self._conn is None:
                return -2
            self._evict_if_expired(key)
            if not self._raw_exists(key):
                return -2
            row = self._conn.execute("SELECT expires_at FROM expiry WHERE key=?",
                                     (key,)).fetchone()
            if not row:
                return -1
            return max(0, int(round(row[0] - self._now())))

    # ----------------------------------------------------------------- hash
    def hset(self, key: str, field: Optional[str] = None, value: Optional[str] = None,
             mapping: Optional[Dict[str, str]] = None) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            items = dict(mapping or {})
            if field is not None:
                items[field] = value
            added = 0
            for f, v in items.items():
                cur = self._conn.execute("SELECT 1 FROM hash WHERE key=? AND field=?",
                                         (key, f)).fetchone()
                if not cur:
                    added += 1
                self._conn.execute("INSERT INTO hash(key,field,value) VALUES(?,?,?) "
                                   "ON CONFLICT(key,field) DO UPDATE SET value=excluded.value",
                                   (key, f, str(v)))
            return added

    def hget(self, key: str, field: str) -> Optional[str]:
        with self._lock:
            if self._conn is None:
                return None
            self._evict_if_expired(key)
            row = self._conn.execute("SELECT value FROM hash WHERE key=? AND field=?",
                                     (key, field)).fetchone()
            return row[0] if row else None

    def hgetall(self, key: str) -> Dict[str, str]:
        with self._lock:
            if self._conn is None:
                return {}
            self._evict_if_expired(key)
            return {f: v for f, v in
                    self._conn.execute("SELECT field,value FROM hash WHERE key=?", (key,))}

    # ----------------------------------------------------------------- list
    def _list_bounds(self, key: str):
        row = self._conn.execute("SELECT MIN(idx), MAX(idx) FROM list WHERE key=?",
                                 (key,)).fetchone()
        return (row[0], row[1]) if row and row[0] is not None else (None, None)

    def lpush(self, key: str, *values: str) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            for v in values:
                lo, _ = self._list_bounds(key)
                nxt = (lo - 1) if lo is not None else 0
                self._conn.execute("INSERT INTO list(key,idx,value) VALUES(?,?,?)",
                                   (key, nxt, str(v)))
            return self.llen(key)

    def rpush(self, key: str, *values: str) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            for v in values:
                _, hi = self._list_bounds(key)
                nxt = (hi + 1) if hi is not None else 0
                self._conn.execute("INSERT INTO list(key,idx,value) VALUES(?,?,?)",
                                   (key, nxt, str(v)))
            return self.llen(key)

    def llen(self, key: str) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            return self._conn.execute("SELECT COUNT(*) FROM list WHERE key=?",
                                      (key,)).fetchone()[0]

    @staticmethod
    def _slice(n: int, start: int, end: int):
        """Redis range semantics: inclusive end, negatives count from the tail."""
        if start < 0:
            start = max(0, n + start)
        if end < 0:
            end = n + end
        end = min(end, n - 1)
        return start, end

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        with self._lock:
            if self._conn is None:
                return []
            self._evict_if_expired(key)
            n = self.llen(key)
            s, e = self._slice(n, start, end)
            if n == 0 or s > e:
                return []
            return [r[0] for r in self._conn.execute(
                "SELECT value FROM list WHERE key=? ORDER BY idx LIMIT ? OFFSET ?",
                (key, e - s + 1, s))]

    def ltrim(self, key: str, start: int, end: int) -> bool:
        with self._lock:
            if self._conn is None:
                return False
            n = self.llen(key)
            s, e = self._slice(n, start, end)
            if n == 0:
                return True
            if s > e:
                self._conn.execute("DELETE FROM list WHERE key=?", (key,))
                return True
            keep = [r[0] for r in self._conn.execute(
                "SELECT idx FROM list WHERE key=? ORDER BY idx LIMIT ? OFFSET ?",
                (key, e - s + 1, s))]
            self._conn.execute(
                f"DELETE FROM list WHERE key=? AND idx NOT IN ({','.join('?' * len(keep))})",
                (key, *keep)) if keep else self._conn.execute(
                "DELETE FROM list WHERE key=?", (key,))
            return True

    # ------------------------------------------------------------------ set
    def sadd(self, key: str, *members: str) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            n = 0
            for m in members:
                cur = self._conn.execute("SELECT 1 FROM set_members WHERE key=? AND member=?",
                                         (key, str(m))).fetchone()
                if not cur:
                    n += 1
                self._conn.execute(
                    "INSERT OR IGNORE INTO set_members(key,member) VALUES(?,?)", (key, str(m)))
            return n

    def smembers(self, key: str) -> set:
        with self._lock:
            if self._conn is None:
                return set()
            self._evict_if_expired(key)
            return {r[0] for r in
                    self._conn.execute("SELECT member FROM set_members WHERE key=?", (key,))}

    def sismember(self, key: str, member: str) -> bool:
        with self._lock:
            if self._conn is None:
                return False
            self._evict_if_expired(key)
            return bool(self._conn.execute(
                "SELECT 1 FROM set_members WHERE key=? AND member=? LIMIT 1",
                (key, str(member))).fetchone())

    def srem(self, key: str, *members: str) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            n = 0
            for m in members:
                cur = self._conn.execute("DELETE FROM set_members WHERE key=? AND member=?",
                                         (key, str(m)))
                n += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            return n

    # ----------------------------------------------------------------- zset
    def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            added = 0
            for m, s in mapping.items():
                cur = self._conn.execute("SELECT 1 FROM zset WHERE key=? AND member=?",
                                         (key, str(m))).fetchone()
                if not cur:
                    added += 1
                self._conn.execute("INSERT INTO zset(key,member,score) VALUES(?,?,?) "
                                   "ON CONFLICT(key,member) DO UPDATE SET score=excluded.score",
                                   (key, str(m), float(s)))
            return added

    def zcard(self, key: str) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            return self._conn.execute("SELECT COUNT(*) FROM zset WHERE key=?",
                                      (key,)).fetchone()[0]

    def zrange(self, key: str, start: int, end: int, desc: bool = False,
               withscores: bool = False) -> List[Any]:
        with self._lock:
            if self._conn is None:
                return []
            self._evict_if_expired(key)
            n = self.zcard(key)
            s, e = self._slice(n, start, end)
            if n == 0 or s > e:
                return []
            order = "DESC" if desc else "ASC"
            rows = self._conn.execute(
                f"SELECT member,score FROM zset WHERE key=? "
                f"ORDER BY score {order}, member {order} LIMIT ? OFFSET ?",
                (key, e - s + 1, s)).fetchall()
            return [(m, sc) for m, sc in rows] if withscores else [m for m, _ in rows]

    def zscore(self, key: str, member: str) -> Optional[float]:
        with self._lock:
            if self._conn is None:
                return None
            row = self._conn.execute("SELECT score FROM zset WHERE key=? AND member=?",
                                     (key, str(member))).fetchone()
            return float(row[0]) if row else None

    @staticmethod
    def _bound(v: Any, default: float) -> float:
        if isinstance(v, str):
            t = v.strip().lower()
            if t in ("-inf", "inf", "+inf"):
                return float(t.replace("+", ""))
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def zrangebyscore(self, key: str, min_score: Any, max_score: Any) -> List[str]:
        with self._lock:
            if self._conn is None:
                return []
            self._evict_if_expired(key)
            lo = self._bound(min_score, float("-inf"))
            hi = self._bound(max_score, float("inf"))
            return [r[0] for r in self._conn.execute(
                "SELECT member FROM zset WHERE key=? AND score>=? AND score<=? "
                "ORDER BY score, member", (key, lo, hi))]

    def zremrangebyrank(self, key: str, start: int, end: int) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            n = self.zcard(key)
            s, e = self._slice(n, start, end)
            if n == 0 or s > e:
                return 0
            doomed = [r[0] for r in self._conn.execute(
                "SELECT member FROM zset WHERE key=? ORDER BY score, member LIMIT ? OFFSET ?",
                (key, e - s + 1, s))]
            if not doomed:
                return 0
            self._conn.execute(
                f"DELETE FROM zset WHERE key=? AND member IN ({','.join('?' * len(doomed))})",
                (key, *doomed))
            return len(doomed)

    def zrem(self, key: str, *members: str) -> int:
        with self._lock:
            if self._conn is None:
                return 0
            n = 0
            for m in members:
                cur = self._conn.execute("DELETE FROM zset WHERE key=? AND member=?",
                                         (key, str(m)))
                n += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            return n

    def hgetall_prefix(self, prefix: str) -> Dict[str, Dict[str, str]]:
        """Every matching hash in ONE indexed SELECT -- the whole point of being on SQL.

        The old read path listed an index and then issued one hgetall PER LESSON: 455 lessons
        meant 455 round-trips, extrapolating to 483 seconds per query at a million. Here the
        engine does it in a single scan of the PRIMARY KEY (key, field) prefix range, and the
        cost stops scaling with the caller's corpus.
        """
        with self._lock:
            if self._conn is None:
                return {}
            out: Dict[str, Dict[str, str]] = {}
            rows = self._conn.execute(
                "SELECT key, field, value FROM hash WHERE key >= ? AND key < ? ORDER BY key",
                (prefix, prefix + "￿")).fetchall()
            now = self._now()
            expired = {k for (k,) in self._conn.execute(
                "SELECT key FROM expiry WHERE expires_at<=?", (now,)).fetchall()}
            for key, field, value in rows:
                if key in expired:
                    continue
                out.setdefault(key, {})[field] = value
            return out

    # ------------------------------------------------------------- keyspace
    def keys(self, pattern: str = "*") -> List[str]:
        """fnmatch, deliberately -- NOT SQLite GLOB. The differential harness compares this
        against FileStore, and GLOB's semantics differ enough to diverge on real patterns."""
        with self._lock:
            if self._conn is None:
                return []
            found = set()
            for t in _DATA_TABLES:
                for (k,) in self._conn.execute(f"SELECT DISTINCT key FROM {t}"):
                    found.add(k)
            for k in list(found):
                if self._evict_if_expired(k):
                    found.discard(k)
            return sorted(k for k in found if fnmatch.fnmatch(k, pattern))

    # ----------------------------------------------- optimistic concurrency
    def cas(self, key: str, expected: Optional[str], value: str) -> bool:
        """Genuinely atomic, and cross-PROCESS -- the property FileStore.cas only appeared to
        have. It compared against its own in-memory dict under a per-instance threading lock,
        so a cross-process probe saw every call return True, zero conflicts, and the other
        writer's key gone. Here the compare happens inside the engine.
        """
        with self._lock:
            if self._conn is None:
                return False
            try:
                self._conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError:
                return False
            try:
                self._evict_if_expired(key)
                row = self._conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
                cur = row[0] if row else None
                want = None if expected is None else str(expected)
                if cur != want:
                    self._conn.execute("ROLLBACK")
                    return False
                self._conn.execute("INSERT INTO kv(key,value) VALUES(?,?) "
                                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                                   (key, str(value)))
                self._conn.execute("DELETE FROM expiry WHERE key=?", (key,))
                self._conn.execute("COMMIT")
                return True
            except Exception:
                try:
                    self._conn.execute("ROLLBACK")
                except Exception:
                    pass
                return False
