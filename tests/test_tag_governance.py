"""
Tag governance G1 -- the confidence-gated, append-only re-tag write path (a CRDT).

The worst-case scenarios are executable invariants here:
  I1 immutability   -- re-tagging never deletes the beat / changes the fact; it moves the index.
  I2 monotonicity   -- a low-confidence record can't override a high/confirmed current (fuzz).
  I3 append-only    -- history only grows.
  I4 reversibility  -- rollback restores a prior tag.
  CRDT convergence  -- the same records in any order yield the same current (commutative/idempotent).

Isolated: injects a temp FileStore. Run: py -m pytest tests/test_tag_governance.py -q
"""
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog
from core.narrative.track_router import RouteHint
from core.narrative.tag_governance import TagGovernor
from core.narrative.schema import beat_key

TRACKS = ["ai-setup", "research", "stemroller", "vision", "voice"]
LOW = ["persist", "generic", "unknown"]


def _setup():
    store = FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))
    log = BeatLog(store)
    gov = TagGovernor(store)
    # seed a beat; a commit touching core/ -> ai-setup at high (path) confidence
    b = log.emit("commit", "Slice 0 schema", "git:abc", at="2026-01-01T00:00:00",
                 hint=RouteHint(paths=["core/narrative/schema.py"]))
    return store, gov, b


def test_higher_confidence_wins_lower_cannot():
    store, gov, b = _setup()                       # seeded ai-setup @ path (0.95)
    changed, cur = gov.record(b.id, "stemroller", source="generic", at="2026-01-02T00:00:00")
    assert cur == "ai-setup" and changed is False, "I2: a generic (0.4) record can't beat path (0.95)"
    changed, cur = gov.record(b.id, "vision", source="path", at="2026-01-03T00:00:00")
    assert cur == "vision" and changed is True, "an equal-or-higher confidence record wins"


def test_confirmed_is_sticky():
    store, gov, b = _setup()
    gov.confirm(b.id, "research", at="2026-01-02T00:00:00")
    # 50 higher-effort auto records of every kind can't dislodge a human confirmation
    for i in range(50):
        gov.record(b.id, random.choice(TRACKS), source="path", at=f"2026-02-{1 + i % 27:02d}T00:00:00")
    assert gov.current(b.id) == "research", "confirmed tag is never auto-overridden"


def test_immutability_and_index_move():
    store, gov, b = _setup()
    assert store.zscore("narr:track:ai-setup:beats", b.id) is not None
    gov.record(b.id, "vision", source="path", at="2026-01-02T00:00:00")  # current -> vision
    # I1: the beat still exists and the FACT is unchanged
    assert store.get(beat_key(b.id)) is not None
    from core.narrative.beat_log import BeatLog as _B
    again = _B(store)._load(b.id)
    assert again.source == "git:abc" and again.summary == "Slice 0 schema", "fact untouched"
    # the index MOVED (not duplicated, not the beat deleted)
    assert store.zscore("narr:track:ai-setup:beats", b.id) is None, "left old track index"
    assert store.zscore("narr:track:vision:beats", b.id) is not None, "joined new track index"


def test_append_only_and_rollback():
    store, gov, b = _setup()
    gov.record(b.id, "stemroller", source="human", at="2026-01-02T00:00:00")  # wrong, confirmed
    assert gov.current(b.id) == "stemroller"
    n_before = len(BeatLog(store)._load(b.id).tag_history)
    changed, cur = gov.rollback(b.id, "ai-setup", at="2026-01-03T00:00:00")
    assert cur == "ai-setup" and changed is True, "I4: rollback restores the prior tag"
    assert len(BeatLog(store)._load(b.id).tag_history) == n_before + 1, "I3: rollback appends, never deletes"


def test_crdt_monotonicity_fuzz():
    """The headline: a confirmed tag + 1000 random low-confidence records, applied in a
    random order, never degrade the current and never touch the fact."""
    store, gov, b = _setup()
    gov.confirm(b.id, "ai-setup", at="2026-01-02T00:00:00")
    rng = random.Random(20260628)
    for i in range(1000):
        gov.record(b.id, rng.choice(TRACKS), source=rng.choice(LOW),
                   at=f"2026-{1 + i % 12:02d}-{1 + i % 27:02d}T{i % 24:02d}:00:00")
    assert gov.current(b.id) == "ai-setup", "I2: no low-confidence storm degrades a confirmed tag"
    fact = BeatLog(store)._load(b.id)
    assert fact.source == "git:abc" and fact.summary == "Slice 0 schema", "I1: fact never changed"


def test_crdt_convergence_order_independent():
    """Same set of records in two different orders -> identical current (commutative)."""
    records = [("research", "category", "2026-03-01T00:00:00"),
               ("vision", "strong", "2026-03-02T00:00:00"),
               ("ai-setup", "path", "2026-03-03T00:00:00"),
               ("stemroller", "generic", "2026-03-04T00:00:00")]
    finals = []
    for order in (records, list(reversed(records)), [records[2], records[0], records[3], records[1]]):
        store, gov, b = _setup()
        for value, source, at in order:
            gov.record(b.id, value, source=source, at=at)
        finals.append(gov.current(b.id))
    assert len(set(finals)) == 1, f"CRDT: order must not matter, got {finals}"
    assert finals[0] == "ai-setup", "the highest-confidence (path) opinion survives regardless of order"


if __name__ == "__main__":
    for fn in [test_higher_confidence_wins_lower_cannot, test_confirmed_is_sticky,
               test_immutability_and_index_move, test_append_only_and_rollback,
               test_crdt_monotonicity_fuzz, test_crdt_convergence_order_independent]:
        fn()
    print("ALL TAG GOVERNANCE G1 TESTS PASSED")
