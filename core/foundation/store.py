"""
Store: Swappable persistence interface (full Redis-mirror)

Semantic Relationship: Store abstracts_persistence_for AllSystems

WHY THIS EXISTS
---------------
Before this, Redis was hardcoded across the codebase and every module
re-implemented its own "try Redis, fall back to files" branching. That made
the backend impossible to swap and duplicated the same logic 5+ times.

`Store` is the single seam. It mirrors the Redis command surface the codebase
actually uses (key/value, hash, list, set, sorted-set, key-scan) so domain
modules can keep their existing data-structure logic but persist THROUGH the
Store instead of talking to Redis directly. Swapping persistence = swapping the
Store instance; no domain code changes.

THREE BACKENDS
--------------
- RedisStore  : real Redis (fast, shared, networked). Built on the fail-fast
                connector so construction never stalls when Redis is down.
- FileStore   : JSON-file emulation of every structure (always available,
                survives restarts, zero infrastructure).
- HybridStore : dual-write to both, read Redis-first with File fallback. This
                is the default for graceful degradation.

VALUE SEMANTICS
---------------
Mirrors redis-py with decode_responses=True: keys, values, hash fields/values,
list items, set members, and zset members are all str. Sorted-set scores are
float. This keeps RedisStore a thin pass-through and FileStore byte-compatible
with what callers already expect.
"""

import os
import json
import time
import shutil
import fnmatch
import threading
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterable, Tuple

from core.foundation.redis_connection import DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT, DEFAULT_REDIS_DB

logger = logging.getLogger("store")


class CASConflict(Exception):
    """Raised by update_atomic when optimistic retries are exhausted (the key kept
    changing under us). Concurrency design C3: a lost update was PREVENTED, not silently
    applied -- the caller should re-read and decide, not blindly overwrite."""


class Store(ABC):
    """
    Abstract persistence interface mirroring the used Redis command surface.

    Semantic Relationship: Store defines_contract_for PersistenceBackends

    Implementations must honor str-in/str-out semantics (decode_responses=True
    equivalent) so backends are interchangeable without caller changes.
    """

    # ----- key/value -----
    @abstractmethod
    def get(self, key: str) -> Optional[str]: ...

    @abstractmethod
    def set(self, key: str, value: str) -> bool: ...

    @abstractmethod
    def delete(self, *keys: str) -> int: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    # ----- expiry (TTL): a key auto-disappears after `seconds` -----
    @abstractmethod
    def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set a key to value that auto-expires after `seconds`."""
        ...

    @abstractmethod
    def expire(self, key: str, seconds: int) -> bool:
        """Attach a TTL to an existing key. False if the key doesn't exist."""
        ...

    @abstractmethod
    def ttl(self, key: str) -> int:
        """Remaining TTL in seconds. Redis semantics: -2 = no such key,
        -1 = key exists but has no expiry, >=0 = seconds remaining."""
        ...

    # ----- hash -----
    @abstractmethod
    def hset(self, key: str, field: Optional[str] = None, value: Optional[str] = None,
             mapping: Optional[Dict[str, str]] = None) -> int: ...

    @abstractmethod
    def hget(self, key: str, field: str) -> Optional[str]: ...

    @abstractmethod
    def hgetall(self, key: str) -> Dict[str, str]: ...

    # ----- list (lpush prepends, like Redis) -----
    @abstractmethod
    def lpush(self, key: str, *values: str) -> int: ...

    @abstractmethod
    def rpush(self, key: str, *values: str) -> int: ...

    @abstractmethod
    def lrange(self, key: str, start: int, end: int) -> List[str]: ...

    @abstractmethod
    def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim a list to the inclusive [start, end] range (-1 = last)."""
        ...

    @abstractmethod
    def llen(self, key: str) -> int: ...

    # ----- set -----
    @abstractmethod
    def sadd(self, key: str, *members: str) -> int: ...

    @abstractmethod
    def smembers(self, key: str) -> set: ...

    @abstractmethod
    def sismember(self, key: str, member: str) -> bool: ...

    @abstractmethod
    def srem(self, key: str, *members: str) -> int:
        """Remove the given members from the set. Returns how many were removed.
        (RB-4, deepseek-mandated: without it a set projection can never shrink --
        the byref index would leak members across every trim cycle.)"""
        ...

    # ----- sorted set -----
    @abstractmethod
    def zadd(self, key: str, mapping: Dict[str, float]) -> int: ...

    @abstractmethod
    def zrange(self, key: str, start: int, end: int, desc: bool = False,
               withscores: bool = False) -> List[Any]: ...

    @abstractmethod
    def zscore(self, key: str, member: str) -> Optional[float]: ...

    @abstractmethod
    def zrangebyscore(self, key: str, min_score: Any, max_score: Any) -> List[str]:
        """Members with min_score <= score <= max_score, ascending. Bounds accept
        numbers or the strings '-inf' / '+inf'."""
        ...

    @abstractmethod
    def zcard(self, key: str) -> int:
        """Number of members in the sorted set."""
        ...

    @abstractmethod
    def zremrangebyrank(self, key: str, start: int, end: int) -> int:
        """Remove members by ascending-score rank, inclusive (-1 = highest).
        Returns how many were removed."""
        ...

    @abstractmethod
    def zrem(self, key: str, *members: str) -> int:
        """Remove the given members from the sorted set. Returns how many were removed."""
        ...

    # ----- keyspace -----
    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]: ...

    def hgetall_prefix(self, prefix: str) -> Dict[str, Dict[str, str]]:
        """Every hash whose key starts with `prefix`, as {key: {field: value}}. ONE round-trip.

        The default below is the naive loop, so no backend breaks by not overriding it -- but
        the naive loop IS the defect this exists to remove, and every real backend should
        override it.

        Why it exists: the lesson corpus was read by listing an index and then issuing ONE
        hgetall PER LESSON. Measured 2026-07-26 at 455 lessons: 220ms per query, 0.483ms per
        lesson, extrapolating to 483 SECONDS per query at a million -- and this sits on the
        PreToolUse path, so it ran on every tool call. The cost was round-trips, not ranking.

        Backends answer this in one operation: SQLite with a single indexed SELECT, FileStore
        straight from the in-memory dict, Redis with a pipeline.
        """
        out: Dict[str, Dict[str, str]] = {}
        for k in self.keys(f"{prefix}*"):
            got = self.hgetall(k)
            if got:
                out[k] = got
        return out

    # ----- optimistic concurrency (C3) -----
    def cas(self, key: str, expected: Optional[str], value: str) -> bool:
        """Compare-and-set: atomically set key=value IFF its current value equals
        `expected` (expected=None means "the key must not exist yet"). Returns True
        if the write happened. This is the lost-update guard for two agents writing
        the same key.

        Default is a NON-atomic get-then-set fallback for unknown backends; the real
        backends (Redis via Lua/NX, File under its lock) override this atomically.
        """
        cur = self.get(key)
        if cur == expected:
            return self.set(key, value)
        return False

    def update_atomic(self, key: str, fn, retries: int = 8) -> Optional[str]:
        """Read-modify-write under optimistic concurrency: read the current value,
        compute fn(current)->new, and cas() it; retry on conflict. Returns the value
        written. Raises CASConflict if `retries` are exhausted. If fn returns None,
        it's a no-op and the current value is returned unchanged."""
        for _ in range(max(1, retries)):
            cur = self.get(key)
            new = fn(cur)
            if new is None:
                return cur
            if self.cas(key, cur, str(new)):
                return str(new)
        raise CASConflict(f"update_atomic: '{key}' kept changing across {retries} retries")

    # ----- lifecycle -----
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this store's primary backend is currently usable."""
        ...

    def close(self) -> None:
        """Release resources. Default: no-op."""
        return None


# =====================================================================
# RedisStore
# =====================================================================
class RedisStore(Store):
    """
    Redis-backed Store. Thin pass-through to a live redis-py client.

    Semantic Relationship: RedisStore located_in Redis

    Construct via `RedisStore.connect(...)` which uses the fail-fast connector,
    so a down Redis yields an unavailable store (is_available() == False) rather
    than a ~48s stall.
    """

    def __init__(self, client: Optional[Any]):
        self._client = client

    @classmethod
    def connect(cls, host: str = DEFAULT_REDIS_HOST, port: int = DEFAULT_REDIS_PORT,
                timeout_seconds: float = 2.0, db: int = DEFAULT_REDIS_DB) -> "RedisStore":
        from core.foundation.redis_connection import connect_to_redis_with_fail_fast
        client = connect_to_redis_with_fail_fast(
            host=host, port=port, timeout_seconds=timeout_seconds, decode_responses=True, db=db
        )
        return cls(client)

    def is_available(self) -> bool:
        return self._client is not None

    # key/value
    def get(self, key): return self._client.get(key)
    def set(self, key, value): return bool(self._client.set(key, value))
    def delete(self, *keys): return int(self._client.delete(*keys)) if keys else 0
    def exists(self, key): return bool(self._client.exists(key))

    # optimistic concurrency (C3): atomic in Redis -- NX for create, Lua for compare
    _CAS_LUA = "if redis.call('GET',KEYS[1])==ARGV[1] then redis.call('SET',KEYS[1],ARGV[2]) return 1 else return 0 end"

    def cas(self, key, expected, value):
        if expected is None:
            return bool(self._client.set(key, str(value), nx=True))
        return bool(self._client.eval(self._CAS_LUA, 1, key, str(expected), str(value)))

    # expiry (TTL)
    def setex(self, key, seconds, value): return bool(self._client.setex(key, int(seconds), value))
    def expire(self, key, seconds): return bool(self._client.expire(key, int(seconds)))
    def ttl(self, key): return int(self._client.ttl(key))

    # hash
    def hset(self, key, field=None, value=None, mapping=None):
        return int(self._client.hset(key, key=field, value=value, mapping=mapping)) \
            if field is not None or mapping else 0
    def hget(self, key, field): return self._client.hget(key, field)
    def hgetall(self, key): return dict(self._client.hgetall(key))

    # list
    def lpush(self, key, *values): return int(self._client.lpush(key, *values))
    def rpush(self, key, *values): return int(self._client.rpush(key, *values))
    def lrange(self, key, start, end): return list(self._client.lrange(key, start, end))
    def ltrim(self, key, start, end): self._client.ltrim(key, start, end); return True
    def llen(self, key): return int(self._client.llen(key))

    # set
    def sadd(self, key, *members): return int(self._client.sadd(key, *members))
    def smembers(self, key): return set(self._client.smembers(key))
    def sismember(self, key, member): return bool(self._client.sismember(key, member))
    def srem(self, key, *members):
        return int(self._client.srem(key, *members)) if members else 0

    # sorted set
    def zadd(self, key, mapping): return int(self._client.zadd(key, mapping))
    def zrange(self, key, start, end, desc=False, withscores=False):
        return list(self._client.zrange(key, start, end, desc=desc, withscores=withscores))
    def zscore(self, key, member):
        s = self._client.zscore(key, member)
        return float(s) if s is not None else None
    def zrangebyscore(self, key, min_score, max_score):
        return list(self._client.zrangebyscore(key, min_score, max_score))
    def zcard(self, key): return int(self._client.zcard(key))
    def zremrangebyrank(self, key, start, end):
        return int(self._client.zremrangebyrank(key, start, end))
    def zrem(self, key, *members):
        return int(self._client.zrem(key, *members)) if members else 0

    # keyspace
    def keys(self, pattern="*"): return list(self._client.keys(pattern))

    def close(self):
        try:
            if self._client is not None:
                self._client.close()
        except Exception:
            pass


# =====================================================================
# FileStore
# =====================================================================
class FileStore(Store):
    """
    File-backed Store. JSON emulation of every Redis structure.

    Semantic Relationship: FileStore located_in File

    Always available, survives restarts, needs no infrastructure. Thread-safe
    via a reentrant lock; writes are atomic (temp file + os.replace). Intended
    as the durable fallback and for environments without Redis.
    """

    # The five Redis structures we model. Expiry is tracked separately as
    # key-scoped metadata (see _expiry), exactly like Redis treats TTL.
    DATA_BUCKETS = ("kv", "hash", "list", "set", "zset")

    def __init__(self, path: Optional[str] = None):
        base = Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "session_logs"
        base.mkdir(parents=True, exist_ok=True)
        self._path = Path(path) if path else base / "store_state.json"
        self._lock = threading.RLock()
        self._data: Dict[str, Dict[str, Any]] = {b: {} for b in self.DATA_BUCKETS}
        self._expiry: Dict[str, float] = {}  # key -> unix expiry timestamp
        # Set when the on-disk state could not be read. While set, this store serves reads
        # and writes from memory but REFUSES to persist -- it will not overwrite bytes it
        # was unable to parse. See _load().
        self._degraded: Optional[str] = None
        self._load()

    def is_available(self) -> bool:
        return True

    # ---- persistence ----
    def _temp_path(self) -> Path:
        """A temp path unique to THIS writer.

        A single shared `<state>.tmp` let concurrent processes interleave their writes into
        one file; the survivor then got renamed into place. That is the origin of the
        "Extra data: line 1 column N" corruption reported live on 2026-07-25 -- two JSON
        documents concatenated in one temp file.
        """
        return self._path.with_suffix(
            f"{self._path.suffix}.{os.getpid()}.{id(self)}.tmp"
        )

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
        except Exception as e:
            self._degraded = f"unreadable: {e}"
            logger.error(
                f"FileStore REFUSING TO PERSIST over {self._path}: {e}. "
                f"In-memory operation continues; the file is left untouched."
            )
            return
        if not raw.strip():
            return  # a fresh or zero-byte file is normal, not an incident
        try:
            loaded = json.loads(raw)
            for bucket in self.DATA_BUCKETS:
                if bucket in loaded:
                    self._data[bucket] = loaded[bucket]
            self._expiry = loaded.get("__expiry__", {})
        except Exception as e:
            # THE INCIDENT GUARD. Previously this logged a warning and returned, leaving
            # _data empty -- and because _flush() serialises the WHOLE state, the next
            # set() wrote that empty dict over the file. A 9MB store became 164 bytes
            # holding one vote. Reproduced at 108963 -> 98 bytes before this guard existed.
            #
            # A read error is survivable. The write it used to license was not. So: keep the
            # bytes for forensics, refuse to persist over them, and stay usable in memory
            # (a hook must never brick the action it decorates).
            self._degraded = f"unparseable: {e}"
            kept = self._preserve_corrupt_bytes()
            if kept:
                logger.error(
                    f"FileStore REFUSING TO PERSIST over {self._path}: {e}. "
                    f"Original bytes preserved at {kept}; in-memory operation continues. "
                    f"Redis remains authoritative -- reconcile the mirror before trusting it."
                )
            else:
                # Never claim a side effect we did not verify. The old code logged
                # "Original bytes preserved" unconditionally while the copy swallowed its
                # own failure -- an operator would be told forensics exist that do not.
                # Same genus as a census OK-line that reads healthy whether or not the work
                # happened; caught by kimi, who had already found that shape twice today.
                logger.error(
                    f"FileStore REFUSING TO PERSIST over {self._path}: {e}. "
                    f"PRESERVATION FAILED -- the corrupt bytes exist ONLY at {self._path} "
                    f"and nothing else holds a copy. Back it up before any recovery attempt. "
                    f"Redis remains authoritative."
                )

    def _preserve_corrupt_bytes(self) -> Optional[Path]:
        """Copy (never move) the unreadable file aside. Returns the copy, or None on failure.

        Copy, because a move races every other process that is about to read it, and
        because the whole point is that we do not yet know which copy is the good one.

        Returns rather than swallows: the caller must not report preservation it cannot
        confirm. Failure here is survivable -- we still refuse to persist, so nothing is
        destroyed -- but the operator has to KNOW the forensic copy is missing, because in
        that case the corrupt file is the only copy left.
        """
        try:
            keep = self._path.with_suffix(
                f"{self._path.suffix}.corrupt.{int(time.time())}.{os.getpid()}"
            )
            if not keep.exists():
                shutil.copy2(self._path, keep)
            return keep if keep.exists() else None
        except Exception:
            return None

    def _flush(self) -> None:
        if self._degraded:
            # Fail CLOSED on persistence only. Reads and writes still work in memory.
            logger.debug(
                f"FileStore not persisting ({self._degraded}); {self._path} left intact."
            )
            return
        tmp = self._temp_path()
        try:
            payload = dict(self._data)
            payload["__expiry__"] = self._expiry
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            # Windows raises WinError 32 when the destination is briefly held open by
            # another reader; that is contention, not corruption, so a short retry is the
            # correct response rather than surfacing an error and dropping the write.
            last: Optional[Exception] = None
            for attempt in range(5):
                try:
                    os.replace(tmp, self._path)
                    return
                except OSError as e:
                    last = e
                    time.sleep(0.02 * (attempt + 1))
            raise last if last else OSError("replace failed")
        except Exception as e:
            logger.error(f"FileStore could not persist {self._path}: {e}")
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass

    # ---- expiry helpers ----
    def _raw_exists(self, key: str) -> bool:
        """Whether key holds data in any structure (ignores expiry/eviction)."""
        return any(key in self._data[b] for b in self.DATA_BUCKETS)

    def _evict_if_expired(self, key: str) -> bool:
        """Lazily drop a key whose TTL has passed. Returns True if evicted."""
        exp = self._expiry.get(key)
        if exp is not None and time.time() >= exp:
            for b in self.DATA_BUCKETS:
                self._data[b].pop(key, None)
            self._expiry.pop(key, None)
            self._flush()
            return True
        return False

    # ---- key/value ----
    def get(self, key):
        with self._lock:
            self._evict_if_expired(key)
            return self._data["kv"].get(key)

    def set(self, key, value):
        with self._lock:
            self._data["kv"][key] = str(value)
            self._expiry.pop(key, None)  # plain set clears any prior TTL (Redis SET behavior)
            self._flush()
            return True

    def delete(self, *keys):
        removed = 0
        with self._lock:
            for key in keys:
                present = False
                for b in self.DATA_BUCKETS:
                    if key in self._data[b]:
                        del self._data[b][key]
                        present = True
                self._expiry.pop(key, None)
                if present:
                    removed += 1
            if removed:
                self._flush()
        return removed

    def hgetall_prefix(self, prefix):
        """One pass over the in-memory hash bucket. No per-key round-trips at all.

        SNAPSHOT THE KEYS FIRST. _evict_if_expired DELETES from the same dict we are walking,
        so iterating it live raised "dictionary changed size during iteration" the moment any
        key in range had an expired TTL. Shipped that way and caught by the FileStore/SQLite
        differential, not by the existing suite -- nothing else exercised expiry through a
        prefix read. A read path that crashes on expiry is worse than the N round-trips it
        replaced, because the slow version was at least correct.
        """
        with self._lock:
            out = {}
            for k in [k for k in self._data["hash"] if k.startswith(prefix)]:
                if self._evict_if_expired(k):
                    continue
                fields = self._data["hash"].get(k)
                if fields:
                    out[k] = dict(fields)
            return out

    def cas(self, key, expected, value):
        # atomic under the reentrant lock: compare current kv to expected, set if equal
        with self._lock:
            self._evict_if_expired(key)
            cur = self._data["kv"].get(key)
            want = None if expected is None else str(expected)
            if cur != want:
                return False
            self._data["kv"][key] = str(value)
            self._expiry.pop(key, None)
            self._flush()
            return True

    def exists(self, key):
        with self._lock:
            self._evict_if_expired(key)
            return self._raw_exists(key)

    # ---- expiry (TTL) ----
    def setex(self, key, seconds, value):
        with self._lock:
            self._data["kv"][key] = str(value)
            self._expiry[key] = time.time() + int(seconds)
            self._flush()
            return True

    def expire(self, key, seconds):
        with self._lock:
            self._evict_if_expired(key)
            if not self._raw_exists(key):
                return False
            self._expiry[key] = time.time() + int(seconds)
            self._flush()
            return True

    def ttl(self, key):
        with self._lock:
            self._evict_if_expired(key)
            if not self._raw_exists(key):
                return -2
            exp = self._expiry.get(key)
            if exp is None:
                return -1
            return max(0, int(exp - time.time()))

    # ---- hash ----
    def hset(self, key, field=None, value=None, mapping=None):
        with self._lock:
            h = self._data["hash"].setdefault(key, {})
            added = 0
            if field is not None:
                if field not in h:
                    added += 1
                h[field] = str(value)
            if mapping:
                for f, v in mapping.items():
                    if f not in h:
                        added += 1
                    h[f] = str(v)
            self._flush()
            return added

    def hget(self, key, field):
        with self._lock:
            self._evict_if_expired(key)
            return self._data["hash"].get(key, {}).get(field)

    def hgetall(self, key):
        with self._lock:
            self._evict_if_expired(key)
            return dict(self._data["hash"].get(key, {}))

    # ---- list (lpush prepends) ----
    def lpush(self, key, *values):
        with self._lock:
            lst = self._data["list"].setdefault(key, [])
            for v in values:
                lst.insert(0, str(v))
            self._flush()
            return len(lst)

    def rpush(self, key, *values):
        with self._lock:
            lst = self._data["list"].setdefault(key, [])
            lst.extend(str(v) for v in values)
            self._flush()
            return len(lst)

    def lrange(self, key, start, end):
        with self._lock:
            self._evict_if_expired(key)
            lst = self._data["list"].get(key, [])
            # Redis end index is inclusive; -1 means last element.
            if end == -1:
                return lst[start:]
            return lst[start:end + 1]

    def ltrim(self, key, start, end):
        with self._lock:
            self._evict_if_expired(key)
            lst = self._data["list"].get(key)
            if lst is None:
                return True  # Redis LTRIM on a missing key is a no-op success
            self._data["list"][key] = lst[start:] if end == -1 else lst[start:end + 1]
            self._flush()
            return True

    def llen(self, key):
        with self._lock:
            self._evict_if_expired(key)
            return len(self._data["list"].get(key, []))

    # ---- set ----
    def sadd(self, key, *members):
        with self._lock:
            s = set(self._data["set"].setdefault(key, []))
            before = len(s)
            s.update(str(m) for m in members)
            self._data["set"][key] = list(s)
            self._flush()
            return len(s) - before

    def smembers(self, key):
        with self._lock:
            self._evict_if_expired(key)
            return set(self._data["set"].get(key, []))

    def sismember(self, key, member):
        with self._lock:
            self._evict_if_expired(key)
            return str(member) in set(self._data["set"].get(key, []))

    def srem(self, key, *members):
        with self._lock:
            s = set(self._data["set"].get(key, []))
            before = len(s)
            s.difference_update(str(m) for m in members)
            if s:
                self._data["set"][key] = list(s)
            else:
                self._data["set"].pop(key, None)   # empty set = absent, like Redis
            self._flush()
            return before - len(s)

    # ---- sorted set ----
    def zadd(self, key, mapping):
        with self._lock:
            z = self._data["zset"].setdefault(key, {})
            added = 0
            for member, score in mapping.items():
                if member not in z:
                    added += 1
                z[str(member)] = float(score)
            self._flush()
            return added

    def zrange(self, key, start, end, desc=False, withscores=False):
        with self._lock:
            self._evict_if_expired(key)
            z = self._data["zset"].get(key, {})
            # W3 differential finding: Redis orders same-score members lexicographically
            # by member; score-only sort leaked dict insertion order and made renders
            # differ by backend (the RB-12 instability, caught by test_store_differential).
            ordered = sorted(z.items(), key=lambda kv: (kv[1], kv[0]), reverse=desc)
            sliced = ordered[start:] if end == -1 else ordered[start:end + 1]
            if withscores:
                return [(m, s) for m, s in sliced]
            return [m for m, _ in sliced]

    def zscore(self, key, member):
        with self._lock:
            self._evict_if_expired(key)
            return self._data["zset"].get(key, {}).get(str(member))

    @staticmethod
    def _score_bound(value, default):
        """Parse a zrangebyscore bound: number, or '-inf'/'+inf' (exclusive
        '(' prefix is tolerated but treated as inclusive)."""
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).lstrip("(")
        if s in ("+inf", "inf"):
            return float("inf")
        if s == "-inf":
            return float("-inf")
        try:
            return float(s)
        except ValueError:
            return default

    def zrangebyscore(self, key, min_score, max_score):
        with self._lock:
            self._evict_if_expired(key)
            z = self._data["zset"].get(key, {})
            lo = self._score_bound(min_score, float("-inf"))
            hi = self._score_bound(max_score, float("inf"))
            # (score, member): Redis tie order -- see zrange (W3 differential finding).
            ordered = sorted(z.items(), key=lambda kv: (kv[1], kv[0]))
            return [m for m, s in ordered if lo <= s <= hi]

    def zcard(self, key):
        with self._lock:
            self._evict_if_expired(key)
            return len(self._data["zset"].get(key, {}))

    def zrem(self, key, *members):
        with self._lock:
            z = self._data["zset"].get(key, {})
            removed = 0
            for m in members:
                if str(m) in z:
                    del z[str(m)]
                    removed += 1
            self._flush()
            return removed

    def zremrangebyrank(self, key, start, end):
        with self._lock:
            self._evict_if_expired(key)
            z = self._data["zset"].get(key)
            if not z:
                return 0
            ordered = [m for m, _ in sorted(z.items(), key=lambda kv: kv[1])]
            n = len(ordered)
            s = start if start >= 0 else n + start
            e = end if end >= 0 else n + end
            s, e = max(0, s), min(n - 1, e)
            # If the resolved range is empty (e.g. a negative rank that points
            # before the list start, like -51 on a 26-element set), remove nothing.
            if e < 0 or s > e:
                return 0
            removed = 0
            for m in ordered[s:e + 1]:
                del z[m]
                removed += 1
            if removed:
                self._flush()
            return removed

    # ---- keyspace -----
    def keys(self, pattern="*"):
        with self._lock:
            # Sweep expired keys first so they don't show up in the listing.
            for k in list(self._expiry):
                self._evict_if_expired(k)
            all_keys = set()
            for b in self.DATA_BUCKETS:
                all_keys.update(self._data[b].keys())
            return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]

    # ---- snapshot (for reconciliation) ----
    def snapshot(self) -> Dict[str, Any]:
        """
        Return a copy of all structures + expiry, for backfilling another backend.

        Semantic Relationship: Snapshot derived_from FileStore (point-in-time copy)
        """
        with self._lock:
            for k in list(self._expiry):
                self._evict_if_expired(k)
            return {
                "kv": dict(self._data["kv"]),
                "hash": {k: dict(v) for k, v in self._data["hash"].items()},
                "list": {k: list(v) for k, v in self._data["list"].items()},
                "set": {k: list(v) for k, v in self._data["set"].items()},
                "zset": {k: dict(v) for k, v in self._data["zset"].items()},
                "expiry": dict(self._expiry),
            }


# =====================================================================
# HybridStore
# =====================================================================
class HybridStore(Store):
    """
    Dual-write Store: writes to Redis (if up) AND File; reads Redis-first.

    Semantic Relationship: HybridStore synchronizes Redis and File

    This is the default. It gives Redis speed when available and File durability
    always. Writes always land in File (the durable record) and best-effort in
    Redis. Reads prefer Redis when available, else fall back to File.
    """

    def __init__(self, redis_store: Optional[RedisStore], file_store: FileStore):
        self._redis = redis_store
        self._file = file_store

    @classmethod
    def create(cls, host: str = DEFAULT_REDIS_HOST, port: int = DEFAULT_REDIS_PORT,
               timeout_seconds: float = 2.0, file_path: Optional[str] = None,
               db: int = DEFAULT_REDIS_DB) -> "HybridStore":
        rs = RedisStore.connect(host=host, port=port, timeout_seconds=timeout_seconds, db=db)
        # T118 D5: the durable tier comes from the ONE backend selector. Hardcoding
        # FileStore here made AKASHIC_STORE_BACKEND=sqlite a lie for every canonical
        # caller (create_store(prefer_redis=True)) -- the flip flipped nothing.
        return cls(rs if rs.is_available() else None, _file_tier(file_path))

    def is_available(self) -> bool:
        return True  # File is always available

    @property
    def redis_available(self) -> bool:
        return self._redis is not None and self._redis.is_available()

    def _read(self):
        """Choose the read backend: Redis if up, else File."""
        return self._redis if self.redis_available else self._file

    def _write(self, method: str, *args, **kwargs):
        """Write to File (durable) always, and Redis (best-effort) if up."""
        result = getattr(self._file, method)(*args, **kwargs)
        if self.redis_available:
            try:
                getattr(self._redis, method)(*args, **kwargs)
            except Exception as e:
                logger.warning(f"HybridStore Redis write '{method}' failed: {e}")
        return result

    # key/value
    def get(self, key): return self._read().get(key)
    def hgetall_prefix(self, prefix):
        """Reads follow the same preference as every other read: Redis when up, else File."""
        return self._read().hgetall_prefix(prefix)
    def set(self, key, value): return self._write("set", key, value)
    def delete(self, *keys): return self._write("delete", *keys)
    def exists(self, key): return self._read().exists(key)

    def cas(self, key, expected, value):
        """CAS against the authoritative backend, then heal the other. When Redis is up
        it is the atomic authority (matches read-Redis-first); on success we mirror to
        File so the durable record converges -- closing the divergence gap. Redis down
        -> File is authority."""
        if self.redis_available:
            ok = self._redis.cas(key, expected, value)
            if ok:
                self._file.set(key, value)   # heal: durable record matches Redis
            return ok
        return self._file.cas(key, expected, value)

    # expiry (TTL)
    def setex(self, key, seconds, value): return self._write("setex", key, seconds, value)
    def expire(self, key, seconds): return self._write("expire", key, seconds)
    def ttl(self, key): return self._read().ttl(key)

    # hash
    def hset(self, key, field=None, value=None, mapping=None):
        return self._write("hset", key, field=field, value=value, mapping=mapping)
    def hget(self, key, field): return self._read().hget(key, field)
    def hgetall(self, key): return self._read().hgetall(key)

    # list
    def lpush(self, key, *values): return self._write("lpush", key, *values)
    def rpush(self, key, *values): return self._write("rpush", key, *values)
    def lrange(self, key, start, end): return self._read().lrange(key, start, end)
    def ltrim(self, key, start, end): return self._write("ltrim", key, start, end)
    def llen(self, key): return self._read().llen(key)

    # set
    def sadd(self, key, *members): return self._write("sadd", key, *members)
    def smembers(self, key): return self._read().smembers(key)
    def sismember(self, key, member): return self._read().sismember(key, member)
    def srem(self, key, *members): return self._write("srem", key, *members)

    # sorted set
    def zadd(self, key, mapping): return self._write("zadd", key, mapping)
    def zrange(self, key, start, end, desc=False, withscores=False):
        return self._read().zrange(key, start, end, desc=desc, withscores=withscores)
    def zscore(self, key, member): return self._read().zscore(key, member)
    def zrangebyscore(self, key, min_score, max_score):
        return self._read().zrangebyscore(key, min_score, max_score)
    def zcard(self, key): return self._read().zcard(key)
    def zremrangebyrank(self, key, start, end):
        return self._write("zremrangebyrank", key, start, end)
    def zrem(self, key, *members):
        return self._write("zrem", key, *members)

    # keyspace
    def keys(self, pattern="*"): return self._read().keys(pattern)

    # ----- reconciliation: keep the two backends consistent -----
    def check_drift(self) -> Dict[str, Any]:
        """
        Report divergence between the File (durable) and Redis backends.

        Semantic Relationship: Drift derived_from File_vs_Redis_KeyComparison

        File is the source of truth, so "missing_in_redis" is the set Redis must
        be backfilled with (the usual case after Redis was down during writes).
        """
        if not self.redis_available:
            return {"redis_available": False, "missing_in_redis": [],
                    "missing_in_file": [], "in_sync": False}
        file_keys = set(self._file.keys("*"))
        redis_keys = set(self._redis.keys("*"))
        missing_in_redis = sorted(file_keys - redis_keys)
        missing_in_file = sorted(redis_keys - file_keys)
        return {
            "redis_available": True,
            "missing_in_redis": missing_in_redis,
            "missing_in_file": missing_in_file,
            "in_sync": not missing_in_redis and not missing_in_file,
        }

    def reconcile(self) -> Dict[str, Any]:
        """
        Heal divergence by backfilling Redis from the durable File snapshot.

        Semantic Relationship: Redis reconciled_from File (File is source of truth)

        Idempotent: re-running on an in-sync pair just rewrites the same values.
        Returns counts of what was written per structure.
        """
        if not self.redis_available:
            return {"status": "skipped", "reason": "redis unavailable"}

        snap = self._file.snapshot()
        written = {"kv": 0, "hash": 0, "list": 0, "set": 0, "zset": 0, "expire": 0}
        # What the heal DECLINED to touch because Redis already held it. Reported, never silent:
        # a heal that quietly skips is how the previous one quietly destroyed.
        skipped = {"list": 0}
        try:
            for k, v in snap["kv"].items():
                self._redis.set(k, v); written["kv"] += 1
            for k, h in snap["hash"].items():
                if h:
                    self._redis.hset(k, mapping=h); written["hash"] += 1
            for k, lst in snap["list"].items():
                # BACKFILL ONLY -- never overwrite a list Redis already holds.
                #
                # This used to delete(k) then rpush the File ordering unconditionally, on the
                # premise "File is source of truth". That premise is FALSE for the learning
                # corpus: measured 2026-07-27, File held a 16-entry learn:experiments:all while
                # Redis held 485. heal_report() calls reconcile() whenever ANY key is missing in
                # Redis, so ONE unrelated drifted key demoted the whole corpus to a 16-lesson
                # fossil and recall went blind to 96% of its own memory -- repeatedly, because
                # it is not an event but every boot that finds drift.
                #
                # The trigger is narrow (specific keys missing) so the action must be too. A key
                # present in BOTH planes is not divergence this reconciler can adjudicate: Redis
                # is the live authority (matches read-Redis-first and cas()), so we leave it
                # alone and SAY we did. Backfilling a key Redis lacks stays exactly as it was.
                #
                # Pin: tests/test_heal_clobbers_richer_redis_list.py
                # Evidence: research/reviewed/index-blindness-RECURRENCE-2026-07-27.md
                if self._redis.exists(k):
                    skipped["list"] += 1
                    continue
                if lst:
                    self._redis.rpush(k, *lst)
                written["list"] += 1
            for k, members in snap["set"].items():
                if members:
                    self._redis.sadd(k, *members); written["set"] += 1
            for k, zmap in snap["zset"].items():
                if zmap:
                    self._redis.zadd(k, zmap); written["zset"] += 1
            now = time.time()
            for k, exp in snap["expiry"].items():
                remaining = int(exp - now)
                if remaining > 0:
                    self._redis.expire(k, remaining); written["expire"] += 1
            return {"status": "success", "written": written, "skipped": skipped}
        except Exception as e:
            logger.error(f"HybridStore reconcile failed: {e}")
            return {"status": "error", "error": str(e), "written": written, "skipped": skipped}

    def heal_report(self) -> List[str]:
        """RB-25 Drill 2 (H2/H2b): the OPERATOR-FACING cold-start heal. check_drift ->
        reconcile the File-ahead side (Redis was behind) -> return render lines that say
        BOTH what was healed AND what was NOT. The reconciler is unidirectional (File is
        source of truth), so a Redis-only key is an orphan the heal cannot and must not
        backfill into File -- but silence about it is the H2b gap: an operator never learns
        the divergence exists. Returns [] when the backends are in sync (no noise).
        Never raises -- a heal that bricks boot is worse than a skipped heal."""
        lines: List[str] = []
        try:
            if not self.redis_available:
                return lines
            drift = self.check_drift()
            if drift.get("missing_in_redis"):
                rep = self.reconcile()
                n = sum((rep.get("written") or {}).values())
                lines.append(f"[heal] Redis was behind -- backfilled {n} key-structure(s) "
                             f"from the durable File (File is source of truth).")
            orphans = drift.get("missing_in_file") or []
            if orphans:
                lines.extend(self._classify_orphans(orphans))   # T081-W5: 3-way honest heal
        except Exception as e:
            lines.append(f"[heal] divergence check failed ({type(e).__name__}) -- skipped, "
                         f"start from the durable File.")
        return lines

    @staticmethod
    def _orphan_family(key) -> str:
        """The family signature of a key (first two ':'-segments) -- the grouping unit for both
        the durable-family check and the count breakdown. Matches how the census groups keys."""
        p = str(key).split(":")
        return ":".join(p[:2]) if len(p) >= 2 else str(key)

    @classmethod
    def _top_families(cls, keys, n: int = 4) -> str:
        from collections import Counter
        c = Counter(cls._orphan_family(k) for k in keys)
        return ", ".join(f"{fam}({cnt})" for fam, cnt in c.most_common(n))

    def _classify_orphans(self, orphans: List[str]) -> List[str]:
        """T081-W5: read the Store-owned durable families (from File), then render the 3-way heal.
        Fail-open: if the File read raises, file_fams=None -> the whole batch stays LOUD."""
        try:
            file_fams = {self._orphan_family(k) for k in self._file.keys("*")}
        except Exception:
            file_fams = None
        return self._render_orphans(orphans, file_fams)

    @classmethod
    def _render_orphans(cls, orphans: List[str], file_fams) -> List[str]:
        """T081-W5 (reconciled 2026-07-16, safety-critical) -- the honest heal, pure + testable.
        A Redis-only key is one of THREE things, not one, so the 4867-key wall becomes a signal:
          (2) DURABLE-family drift -- its family is Store-owned (in File); Redis just holds more
              (append/TTL-trimmed). Calm + visible, NOT a data-loss alarm.
          (1) EPHEMERAL-by-design -- transport/control/telemetry/drill (packet_spec roster). Quiet.
          (3) UNKNOWN -- neither: the genuine 'a write never reached the durable side'. LOUD.
        Order IS the safety guarantee: durable check FIRST (File is truth -- the roster can never
        silence a Store-owned family), roster second, unknown last. file_fams=None -> fail-open:
        the whole batch is LOUD. Counts are lossless: unknown + durable + ephemeral == len(orphans)."""
        # W03 (kimi F3): heal lines are ABOUT the shared Redis/File keyspace, never the
        # booting seat's task -- the [fleet-hygiene] tag says so, so an all-caps INVESTIGATE
        # stops reading as a newcomer's first-minute assignment (their walk mis-diagnosed it).
        TAG = "[heal][fleet-hygiene]"
        if file_fams is None:                             # classification unavailable -> all loud
            shown = ", ".join(orphans[:5]) + (" ..." if len(orphans) > 5 else "")
            return [f"{TAG} {len(orphans)} Redis-only key(s) have NO File record "
                    f"(classification unavailable -- ALL flagged): {shown}. "
                    f"Investigate -- a write that never reached the durable side."]
        from core.comm.packet_spec import is_ephemeral_key
        durable, ephemeral, unknown = [], [], []
        for k in orphans:
            if cls._orphan_family(k) in file_fams:        # File is truth -- checked FIRST
                durable.append(k)
            elif is_ephemeral_key(k):
                ephemeral.append(k)
            else:
                unknown.append(k)
        out: List[str] = []
        if unknown:                                       # most-severe first -- the real signal
            shown = ", ".join(unknown[:5]) + (" ..." if len(unknown) > 5 else "")
            out.append(f"{TAG} {len(unknown)} UNKNOWN Redis-only key(s) -- no File record, not "
                       f"ephemeral-by-design: {shown}. INVESTIGATE (owner: whoever mints this "
                       f"family, not the booting seat) -- a write that never reached the "
                       f"durable side.")
        if durable:
            out.append(f"{TAG} {len(durable)} durable-family key(s) Redis-ahead of File "
                       f"({cls._top_families(durable)}) -- expected for append/TTL-trimmed "
                       f"families; investigate only if growing.")
        if ephemeral:
            out.append(f"{TAG} {len(ephemeral)} expected Redis-only key(s) "
                       f"({cls._top_families(ephemeral)}) -- transport/control/telemetry/drill, "
                       f"no action.")
        return out

    def close(self):
        # T118 D7: both tiers, exactly once. Closing only Redis leaked the SQLite
        # handle -- harmless for FileStore (no-op close), but on Windows an open
        # SQLite connection blocks exactly the checkpoint/swap/rollback file ops a
        # cutover depends on.
        if self._redis is not None:
            self._redis.close()
        durable_close = getattr(self._file, "close", None)
        if callable(durable_close):
            durable_close()


# =====================================================================
# DictStore (Wave 3 -- the differential reference backend)
# =====================================================================
class DictStore(FileStore):
    """Pure in-memory Store: FileStore's structure semantics with NO disk and NO TTL.

    Semantic Relationship: DictStore emulates RedisStore

    Built for the Wave 3 differential harness (docs/library/design/20260711_wave-3-reconciled-build-spec-rb-8-12-dic_4f427b.md): the
    same op sequence runs against DictStore and RedisStore, and any divergence -- in
    return values or final state -- IS the finding. Also the zero-I/O backend unit
    tests want. TTL ops refuse loudly rather than lie (Wave 3 cut list: a backend that
    cannot expire must say so): setex/expire/ttl raise NotImplementedError."""

    def __init__(self):
        self._path = None
        self._lock = threading.RLock()
        self._data = {b: {} for b in self.DATA_BUCKETS}
        self._expiry = {}

    def _load(self):
        pass

    def _flush(self):
        pass

    def setex(self, key, seconds, value):
        raise NotImplementedError("DictStore has no TTL by design (W3 cut list)")

    def expire(self, key, seconds):
        raise NotImplementedError("DictStore has no TTL by design (W3 cut list)")

    def ttl(self, key):
        raise NotImplementedError("DictStore has no TTL by design (W3 cut list)")


# =====================================================================
# Factory
# =====================================================================
def create_store(prefer_redis: bool = True, host: str = DEFAULT_REDIS_HOST, port: int = DEFAULT_REDIS_PORT,
                  timeout_seconds: float = 2.0, file_path: Optional[str] = None,
                  db: int = DEFAULT_REDIS_DB) -> Store:
    """
    Create the default Store for the system.

    Semantic Relationship: Store derives_from AvailableBackends

    - prefer_redis=True  -> HybridStore (Redis when up, File always; dual-write)
    - prefer_redis=False -> FileStore only (no Redis probe at all)

    Always returns a usable Store; never raises on a down Redis.
    """
    if not prefer_redis:
        return _file_tier(file_path)
    return HybridStore.create(host=host, port=port, timeout_seconds=timeout_seconds,
                              file_path=file_path, db=db)


def _file_tier(file_path: Optional[str] = None) -> Store:
    """The durable file tier: SqliteStore when opted in, FileStore otherwise.

    OPT-IN ON PURPOSE, and it must stay opt-in until the canonical store is migrated.
    SqliteStore reads store_state.DB; the live data is in store_state.JSON. Flipping this
    default before migrating would hand every consumer a syntactically perfect, completely
    EMPTY store -- a confidently-wrong answer, which is the exact failure genus this backend
    exists to remove. Migrate first (py -m core.foundation.migrate_to_sqlite, which verifies
    value-by-value and leaves the JSON untouched), then flip.

    Why the swap is one line: create_store() is the universal factory. No production code
    imports FileStore directly (deepseek's census: zero imports outside store.py and
    learning_store.py), so every caller inherits the backend from here.

    AKASHIC_STORE_BACKEND=sqlite  -> SqliteStore
    unset / anything else         -> FileStore (today's default)
    """
    if (os.getenv("AKASHIC_STORE_BACKEND") or "").strip().lower() == "sqlite":
        from core.foundation.sqlite_store import SqliteStore  # late: avoids an import cycle
        path = file_path
        echo = file_path
        if path and path.endswith(".json"):
            path = path[:-len(".json")] + ".db"
        elif path is None:
            # Defaults pair store_state.db with store_state.json -- the same twin the
            # migration and the dual-authority checker reason about.
            echo = os.path.join(os.getenv("AI_SETUP", r"E:\AI-Setup"),
                                "session_logs", "store_state.json")
        else:
            echo = None  # a bare .db path names no JSON twin; nothing to escrow to
        # T118 D4: while the cutover era lasts, closing a sqlite-selected store exports
        # the full state to the JSON twin, so the advertised rollback ("select the file
        # backend again") finds every post-flip write instead of a frozen twin.
        return SqliteStore(path, echo_json_path=echo)
    return FileStore(file_path)
