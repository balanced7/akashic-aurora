"""
Tests for the Ledger event-record interface (Pillar 0) and the
AgentSignalLedger that runs on top of it.

Run: py tests/test_ledger.py
"""

import sys
import os
import tempfile
import isolate_canonical  # noqa: F401 -- isolates file store (AI_SETUP) + Redis db 15 BEFORE foundation import

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.ledger import Ledger, FileLedger, RedisLedger, HybridLedger, create_ledger
from core.signals.agent_signal_ledger import AgentSignalLedger


def _exercise_ledger(ledger: Ledger, label: str) -> None:
    """Append-and-replay semantics that every backend must honor."""
    print(f"\n--- {label} ---")
    stream = "test:stream"

    id1 = ledger.emit(stream, {"n": 1, "msg": "first"})
    id2 = ledger.emit(stream, {"n": 2, "msg": "second"})
    id3 = ledger.emit(stream, {"n": 3, "msg": "third"})
    assert id1 and id2 and id3, "emit must return ids"

    events = ledger.consume(stream, after_id="0")
    assert [e["n"] for _id, e in events] == [1, 2, 3], f"replay order wrong: {events}"
    assert events[0][1]["msg"] == "first"
    print("  emit/consume: append + replay oldest-first OK")

    after_first = ledger.consume(stream, after_id=id1)
    assert [e["n"] for _id, e in after_first] == [2, 3], f"cursor resume wrong: {after_first}"
    print("  cursor: after_id resumes past consumed events OK")

    capped = ledger.consume(stream, after_id="0", count=2)
    assert len(capped) == 2, f"count cap failed: {capped}"
    print("  count: batch size capped OK")

    tail = ledger.consume(stream, after_id=events[-1][0])
    assert tail == [], f"expected empty tail, got {tail}"
    print("  tail: nothing new after last id OK")

    ledger.emit(stream, {"nested": {"a": [1, 2], "b": "x"}})
    last = ledger.consume(stream, after_id=events[-1][0])
    assert last[-1][1]["nested"]["a"] == [1, 2]
    print("  payload: nested dict round-trips OK")


def test_fileledger():
    with tempfile.TemporaryDirectory() as d:
        _exercise_ledger(FileLedger(d), "FileLedger")


def test_fileledger_maxlen():
    with tempfile.TemporaryDirectory() as d:
        ledger = FileLedger(d)
        for i in range(10):
            ledger.emit("capped", {"i": i}, maxlen=3)
        kept = ledger.consume("capped", after_id="0", count=100)
        assert [e["i"] for _id, e in kept] == [7, 8, 9], f"maxlen trim wrong: {kept}"
        new_id = ledger.emit("capped", {"i": 10}, maxlen=3)
        assert int(new_id) > int(kept[-1][0]), "ids must keep increasing after trim"
        print("\n--- FileLedger maxlen ---\n  trim-to-newest + monotonic ids OK")


def test_hybridledger_redis_down():
    with tempfile.TemporaryDirectory() as d:
        ledger = HybridLedger.create(port=63999, base_dir=d)
        assert ledger.redis_available is False, "expected Redis unavailable on bogus port"
        _exercise_ledger(ledger, "HybridLedger (Redis down -> File)")
        print("  hybrid: graceful File fallback OK")


def test_factory():
    with tempfile.TemporaryDirectory() as d:
        file_only = create_ledger(prefer_redis=False, base_dir=d)
        assert isinstance(file_only, FileLedger)
        hybrid = create_ledger(prefer_redis=True, port=63999, base_dir=d)
        assert isinstance(hybrid, HybridLedger)
        print("\n--- factory ---\n  create_ledger routing OK")


def test_agent_signal_ledger():
    """The signal-specific ledger: append fans out to per-agent + canonical."""
    with tempfile.TemporaryDirectory() as d:
        sl = AgentSignalLedger(ledger=FileLedger(d))
        sl.append_signal({"agent_id": "a1", "signal_type": "decision", "signal_number": 0, "x": 1})
        sl.append_signal({"agent_id": "a2", "signal_type": "blocker", "signal_number": 0, "x": 2})
        sl.append_signal({"agent_id": "a1", "signal_type": "action", "signal_number": 1, "x": 3})

        # Canonical firehose holds every agent's signals, in order.
        fire = sl.replay_signals(after_id="0")
        assert [s["signal_type"] for _id, s in fire] == ["decision", "blocker", "action"], fire
        print("\n--- AgentSignalLedger ---\n  canonical firehose: all agents in order OK")

        # Per-agent stream holds only that agent's signals.
        a1 = sl.ledger.consume(sl.stream_for_agent("a1"), after_id="0")
        assert [s["signal_type"] for _id, s in a1] == ["decision", "action"], a1
        print("  per-agent stream: only that agent's signals OK")

        # Cursor resume on the firehose.
        first_id = fire[0][0]
        rest = sl.replay_signals(after_id=first_id)
        assert [s["signal_type"] for _id, s in rest] == ["blocker", "action"], rest
        print("  cursor resume on firehose OK")


def test_redisledger_if_available():
    from redis_test_helpers import fresh_test_ledger
    rl = fresh_test_ledger()   # isolated test DB (15), flushed clean; never canonical db 0
    if rl is None:
        print("\n--- RedisLedger ---\n  SKIPPED (Redis not running)")
        return
    stream = "test:ledger:stream"
    id1 = rl.emit(stream, {"n": 1})
    rl.emit(stream, {"n": 2})
    events = rl.consume(stream, after_id="0")
    assert [e["n"] for _id, e in events] == [1, 2], f"live replay wrong: {events}"
    after = rl.consume(stream, after_id=id1)
    assert [e["n"] for _id, e in after] == [2]
    rl._client.flushdb()   # leave the test DB clean
    print("\n--- RedisLedger (live) ---\n  live append+replay+cursor OK")


if __name__ == "__main__":
    print("=" * 60)
    print("LEDGER TESTS")
    print("=" * 60)
    test_fileledger()
    test_fileledger_maxlen()
    test_hybridledger_redis_down()
    test_factory()
    test_agent_signal_ledger()
    test_redisledger_if_available()
    print("\n" + "=" * 60)
    print("ALL LEDGER TESTS PASSED")
    print("=" * 60)
