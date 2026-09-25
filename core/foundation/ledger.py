"""
Ledger: Swappable event-record interface (append-and-replay)

Semantic Relationship: Ledger records_events_for Agents

WHY THIS EXISTS (and why it is NOT the Store, nor a message bus)
---------------------------------------------------------------
`Store` answers "what IS the current value of X?" -- state you read back by key.
`Ledger` answers "what HAPPENED, in order?" -- events you append and replay.
These are two different mental models, and Redis itself models them differently
(key/value/hash/etc. vs. streams). Conflating them under one interface would
make every call site ambiguous, so events get their own primitive, symmetric
with Store. Store + Ledger is the classic systems pairing: the store holds
current values, the ledger records the ordered sequence of events.

This is NOT a real-time message bus: nothing is pushed. An emitter appends an
event; a reader replays everything after a bookmark (cursor), in order, whenever
it wants. It is a durable, ordered, replayable record -- a ledger.

Relationship to chronicles/: this ledger is the RAW firehose -- every event
every agent emits. A "chronicle" (the curated highlights: decisions, failures,
milestones) is a distilled view DERIVED FROM this ledger, not the ledger
itself. Keep the two distinct: ledger = everything in order, chronicle = the
significant few.

Use the Ledger for signal transport (an agent emits a DECISION; the coordinator
replays the stream and reacts). Use the Store for queryable state (a learning
you look up later). Recording a fact -> Store. Announcing something that
happened -> Ledger.

THREE BACKENDS (mirrors Store exactly)
--------------------------------------
- RedisLedger  : Redis Streams (xadd/xread). Built on the fail-fast connector,
                  so a down Redis yields an unavailable ledger rather than a stall.
- FileLedger   : append-only JSONL per stream (always available, survives
                  restarts, zero infrastructure). The durable record.
- HybridLedger : append to both, read Redis-first with File fallback. Default.

EVENT MODEL
-----------
Callers emit and receive plain dicts. The Ledger owns the wire detail (Redis
stores each event as a {"data": <json>} field map; FileLedger stores one JSON
line per event). Each event gets an id; consumers pass the last id back as
`after_id` to resume. Ids are backend-specific and only comparable within one
backend -- consumers should treat them as opaque cursors and dedup downstream if
a backend switch replays (the coordinator already dedups by agent_id:signal_number).
"""

import os
from core.paths import data_root
import re
import json
import time
import threading
import logging
import contextlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.foundation.redis_connection import DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT, DEFAULT_REDIS_DB
from core.foundation import filelock

logger = logging.getLogger("ledger")

# How far back emit() reads to find the newest complete record (one chunk covers any sane
# line), and how far it will scan past torn or foreign lines before a full read instead.
_TAIL_CHUNK = 64 * 1024
_TAIL_LIMIT = 4 * 1024 * 1024

# An event as handed to/from callers, paired with its cursor id.
Event = Tuple[str, Dict[str, Any]]


class Ledger(ABC):
    """
    Abstract event-record interface (append-only log with replay).

    Semantic Relationship: Ledger defines_contract_for EventBackends

    Implementations append events to named streams and replay them after a
    cursor. Callers deal in plain dicts; the Ledger owns serialization.
    """

    @abstractmethod
    def emit(self, stream: str, event: Dict[str, Any], maxlen: Optional[int] = None) -> str:
        """
        Append an event to a stream. Returns the new event's cursor id.

        Semantic Relationship: Event appended_to Stream

        `maxlen`, if given, caps the stream to roughly its newest `maxlen`
        events (older ones are trimmed).
        """
        ...

    @abstractmethod
    def consume(self, stream: str, after_id: str = "0", count: int = 100,
                block_ms: int = 0) -> List[Event]:
        """
        Replay events appended after `after_id`, oldest first.

        Semantic Relationship: Events replayed_from Stream

        Returns a list of (id, event) pairs, at most `count`. `after_id="0"`
        reads from the beginning. `block_ms`>0 waits up to that long for new
        events when none are immediately available.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this ledger's primary backend is currently usable."""
        ...

    def close(self) -> None:
        """Release resources. Default: no-op."""
        return None


# =====================================================================
# RedisLedger
# =====================================================================
class RedisLedger(Ledger):
    """
    Redis Streams-backed Ledger. Thin pass-through to a live redis-py client.

    Semantic Relationship: RedisLedger located_in RedisStreams

    Construct via `RedisLedger.connect(...)` which uses the fail-fast connector,
    so a down Redis yields an unavailable ledger (is_available() == False).
    """

    def __init__(self, client: Optional[Any]):
        self._client = client

    @classmethod
    def connect(cls, host: str = DEFAULT_REDIS_HOST, port: int = DEFAULT_REDIS_PORT,
                timeout_seconds: float = 2.0, db: int = DEFAULT_REDIS_DB) -> "RedisLedger":
        from core.foundation.redis_connection import connect_to_redis_with_fail_fast
        client = connect_to_redis_with_fail_fast(
            host=host, port=port, timeout_seconds=timeout_seconds, decode_responses=True, db=db
        )
        return cls(client)

    def is_available(self) -> bool:
        return self._client is not None

    def emit(self, stream, event, maxlen=None):
        kwargs = {}
        if maxlen is not None:
            kwargs["maxlen"] = maxlen
            kwargs["approximate"] = True  # cheaper, near-exact trim
        return str(self._client.xadd(stream, {"data": json.dumps(event)}, **kwargs))

    def consume(self, stream, after_id="0", count=100, block_ms=0):
        block = block_ms if block_ms > 0 else None
        raw = self._client.xread({stream: after_id}, count=count, block=block)
        events: List[Event] = []
        for _stream, messages in raw or []:
            for message_id, fields in messages:
                try:
                    event = json.loads(fields.get("data", "{}"))
                except (json.JSONDecodeError, TypeError):
                    event = {}
                events.append((str(message_id), event))
        return events

    def close(self):
        try:
            if self._client is not None:
                self._client.close()
        except Exception:
            pass


# =====================================================================
# FileLedger
# =====================================================================
class FileLedger(Ledger):
    """
    File-backed Ledger. Append-only JSONL, one file per stream.

    Semantic Relationship: FileLedger located_in File

    Always available, survives restarts, needs no infrastructure; the durable record of
    every event. Cursor ids are a monotonic per-stream integer (as a string) so they stay
    comparable even after `maxlen` trimming.

    CROSS-PROCESS (2026-09-24, L0 of the DuckDB synthesis). emit() appends ONE line while
    holding an OS lock every process shares (core.foundation.filelock, a sidecar
    `<stream>.jsonl.lock`), and reads only the file's tail to find the next id. It used to
    read the whole file, rewrite it through one fixed tmp name and os.replace it, guarded by
    a threading lock no other process could see: two writers read the same state, the later
    replace won, and the other row vanished -- 410 of 18,170 recall outcomes, 09-10..24.
    On Windows os.replace also fails while any reader holds the file open, and that failure
    was swallowed after emit had already chosen an id. Pinned in
    tests/test_ledger_cross_process.py.

    `maxlen` trimming is amortized: a stream may run maxlen // 10 rows past its cap before
    one rewrite trims it back to the newest `maxlen` (exact for small caps) -- the "roughly"
    the Ledger contract always promised. A trim that cannot replace the file because a reader
    holds it is skipped and retried by a later emit. The row was appended before the trim was
    attempted, so a failed trim costs disk, never data.
    """

    def __init__(self, base_dir: Optional[str] = None):
        base = Path(base_dir) if base_dir else \
            data_root() / "session_logs" / "ledger"
        base.mkdir(parents=True, exist_ok=True)
        self._base = base
        self._lock = threading.RLock()

    def is_available(self) -> bool:
        return True

    def _stream_path(self, stream: str) -> Path:
        # Sanitize ':' '/' etc. so a stream name maps to one safe filename.
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", stream)
        return self._base / f"{safe}.jsonl"

    def _read_records(self, stream: str) -> List[Dict[str, Any]]:
        path = self._stream_path(stream)
        if not path.exists():
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    def emit(self, stream, event, maxlen=None):
        path = self._stream_path(stream)
        last_id = 0
        with self._lock:
            try:
                with filelock.exclusive(path):
                    last_id, torn = self._tail_state(path)
                    record = {"id": str(last_id + 1), "event": event}
                    line = json.dumps(record) + "\n"
                    with open(path, "a", encoding="utf-8") as f:
                        # A torn last line (power cut mid-write) gets its own line break, so
                        # it cannot glue itself onto this record; readers skip it as before.
                        f.write(("\n" + line) if torn else line)
                    if maxlen is not None:
                        self._maybe_trim(path, maxlen, last_id + 1)
                    return record["id"]
            except Exception as e:
                # Loud, never raising: emit sits on hot paths in every seat. A lock timeout
                # (10 s of contention) or a disk error loses this one event WITH a log line;
                # the returned id is the newest one on disk, so no cursor goes backwards.
                logger.error(f"FileLedger could not append to {path}: {e}")
                return str(last_id)

    @staticmethod
    def _tail_state(path: Path) -> Tuple[int, bool]:
        """(the id of the newest complete record, whether the file ends mid-line).

        Reads backwards from the end in chunks, skipping torn or foreign lines. Falls back to
        a full read only if nothing parses within _TAIL_LIMIT bytes.
        """
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return 0, False
        if size == 0:
            return 0, False
        with open(path, "rb") as f:
            f.seek(size - 1)
            torn = f.read(1) != b"\n"
            pos, carry, scanned = size, b"", 0
            while pos > 0 and scanned < _TAIL_LIMIT:
                step = min(_TAIL_CHUNK, pos)
                pos -= step
                f.seek(pos)
                pieces = (f.read(step) + carry).split(b"\n")
                scanned += step
                # pieces[0] may be the tail of a longer line unless we reached byte 0.
                carry = pieces[0] if pos > 0 else b""
                for raw in reversed(pieces if pos == 0 else pieces[1:]):
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        return int(json.loads(raw)["id"]), torn
                    except (ValueError, KeyError, TypeError):
                        continue
        records = FileLedger._parse_file(path)
        return max((int(r["id"]) for r in records if "id" in r), default=0), torn

    @staticmethod
    def _head_id(path: Path) -> Optional[int]:
        """Id of the oldest complete record, from the first lines only; None if unknown."""
        with contextlib.suppress(OSError):
            with open(path, "rb") as f:
                for _ in range(32):
                    raw = f.readline(_TAIL_CHUNK * 16)
                    if not raw:
                        break
                    with contextlib.suppress(ValueError, KeyError, TypeError):
                        return int(json.loads(raw.strip())["id"])
        return None

    def _maybe_trim(self, path: Path, maxlen: int, newest_id: int) -> None:
        """Trim to the newest `maxlen` once the stream is maxlen // 10 past its cap.

        Runs under the caller's cross-process lock. Ids are contiguous under that lock, so
        newest - oldest + 1 counts the rows without reading the file.
        """
        oldest = self._head_id(path)
        count = (newest_id - oldest + 1) if oldest is not None else None
        if count is not None and count <= maxlen + maxlen // 10:
            return
        records = self._parse_file(path)
        if len(records) <= maxlen:
            return
        tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                for r in records[-maxlen:]:
                    f.write(json.dumps(r) + "\n")
            os.replace(tmp, path)
        except OSError as e:
            logger.warning(f"FileLedger trim of {path.name} deferred to a later emit: {e}")
            with contextlib.suppress(OSError):
                tmp.unlink()

    @staticmethod
    def _parse_file(path: Path) -> List[Dict[str, Any]]:
        records = []
        with contextlib.suppress(FileNotFoundError):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def consume(self, stream, after_id="0", count=100, block_ms=0):
        with self._lock:
            events = self._collect_after(stream, after_id, count)
        if events or block_ms <= 0:
            return events
        # Polite single wait-then-recheck so a polling loop doesn't busy-spin.
        time.sleep(min(block_ms, 1000) / 1000.0)
        with self._lock:
            return self._collect_after(stream, after_id, count)

    def _collect_after(self, stream: str, after_id: str, count: int) -> List[Event]:
        try:
            cursor = int(after_id)
        except (TypeError, ValueError):
            cursor = 0
        events: List[Event] = []
        for r in self._read_records(stream):
            if int(r["id"]) > cursor:
                events.append((r["id"], r["event"]))
                if len(events) >= count:
                    break
        return events


# =====================================================================
# HybridLedger
# =====================================================================
class HybridLedger(Ledger):
    """
    Dual-write Ledger: appends to Redis (if up) AND File; reads Redis-first.

    Semantic Relationship: HybridLedger synchronizes RedisStreams and File

    This is the default. Events always land in File (the durable record) and
    best-effort in Redis. Reads prefer Redis when available, else File. Cursor
    ids returned by emit() come from the active read backend, so a consumer's
    `after_id` stays consistent with what consume() will read.
    """

    def __init__(self, redis_ledger: Optional[RedisLedger], file_ledger: FileLedger):
        self._redis = redis_ledger
        self._file = file_ledger

    @classmethod
    def create(cls, host: str = DEFAULT_REDIS_HOST, port: int = DEFAULT_REDIS_PORT,
               timeout_seconds: float = 2.0, base_dir: Optional[str] = None,
               db: int = DEFAULT_REDIS_DB) -> "HybridLedger":
        rj = RedisLedger.connect(host=host, port=port, timeout_seconds=timeout_seconds, db=db)
        return cls(rj if rj.is_available() else None, FileLedger(base_dir))

    def is_available(self) -> bool:
        return True  # File is always available

    @property
    def redis_available(self) -> bool:
        return self._redis is not None and self._redis.is_available()

    def emit(self, stream, event, maxlen=None):
        # File is the durable record -- always write it.
        file_id = self._file.emit(stream, event, maxlen=maxlen)
        if self.redis_available:
            try:
                # Return the Redis id, since reads will come from Redis.
                return self._redis.emit(stream, event, maxlen=maxlen)
            except Exception as e:
                logger.warning(f"HybridLedger Redis emit failed: {e}")
        return file_id

    def consume(self, stream, after_id="0", count=100, block_ms=0):
        backend = self._redis if self.redis_available else self._file
        return backend.consume(stream, after_id=after_id, count=count, block_ms=block_ms)

    def close(self):
        if self._redis is not None:
            self._redis.close()


# =====================================================================
# Factory
# =====================================================================
def create_ledger(prefer_redis: bool = True, host: str = DEFAULT_REDIS_HOST, port: int = DEFAULT_REDIS_PORT,
                   timeout_seconds: float = 2.0, base_dir: Optional[str] = None,
                   db: int = DEFAULT_REDIS_DB) -> Ledger:
    """
    Create the default Ledger for the system.

    Semantic Relationship: Ledger derives_from AvailableBackends

    - prefer_redis=True  -> HybridLedger (Redis when up, File always; dual-write)
    - prefer_redis=False -> FileLedger only (no Redis probe at all)

    Always returns a usable Ledger; never raises on a down Redis.
    """
    if not prefer_redis:
        return FileLedger(base_dir)
    return HybridLedger.create(host=host, port=port, timeout_seconds=timeout_seconds,
                                base_dir=base_dir, db=db)
