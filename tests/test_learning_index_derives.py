"""PRE-REGISTERED ACCEPTANCE -- lesson index membership DERIVES from the hash plane.

THE RECEIPT (2026-07-27, Daniel's overnight reliability mandate): 464 lesson records existed
and the index held 16. 446 lessons -- 96% of the fleet's institutional memory -- were invisible
to every recall read path (at_action's hot path, funnel, curator, knowledge_map,
relevance_budget, boot's learning_loader). recall was ranking, surfacing, curating AND MEASURING
ITSELF over 3.5% of its corpus, and the funnel's "value 5.9%" was computed on that sample.

It had already been found and repaired ONCE (2026-07-25: 24 of 406, repaired to 434). It
recurred within two days. The detector built to catch recurrence -- repair_learning_index.py
--check -- was never wired to a gate, so the recurrence was silent. That is W69 a third time.

THE ROOT CAUSE OF PERSISTENCE, learning_store.py:449:
    is_new = not self.store.exists(f"learn:experiment:{id}")
    hset(...); if is_new: lpush(INDEX, id)
`is_new` keys on HASH existence, not INDEX membership. Once an id leaves the index while its
hash lives, every later write sees is_new=False and skips the lpush. The index cannot rebuild
itself through its own write path -- self-sealing by construction.

THE FIX, agreed by both halves of the fence (claude + deepseek, 2026-07-27, rounds 1-2):
the index is a CACHED PROJECTION over the hash plane, not an independent artifact. Membership
DERIVES; it never accumulates. deepseek's prior-art half settled the strategy: materialized-view
maintenance says FULL REBUILD beats incremental repair when the mutation log is unreliable --
and ours is provably unreliable.

Run: py -m pytest tests/test_learning_index_derives.py -q
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

INDEX = "learn:experiments:all"


def _fresh_store():
    from core.foundation.store import FileStore
    import tempfile
    d = tempfile.mkdtemp(prefix="lidx-")
    return FileStore(base_dir=d) if "base_dir" in FileStore.__init__.__code__.co_varnames \
        else FileStore()


@pytest.fixture()
def ls(monkeypatch, tmp_path):
    monkeypatch.setenv("_AISETUP_TEST_ISOLATED", "1")
    monkeypatch.setenv("AI_SETUP", str(tmp_path))
    from core.learning.learning_store import LearningStore
    from core.foundation.store import FileStore
    store = FileStore()
    s = LearningStore(store=store)
    try:
        s.store.delete(INDEX)
    except Exception:
        pass
    return s


def _record(s, name, **over):
    sig = {"experiment_name": name, "what_tried": "t", "actual_outcome": "a",
           "success": "yes", "recommendation": "r", "agent_id": "claude"}
    sig.update(over)
    s.persist_learning_derived_from_experiment(sig)


def test_p1_an_orphaned_hash_returns_on_the_next_write():
    """THE SELF-HEAL THE OLD CODE COULD NOT DO. Simulate the live defect exactly: records
    exist, the index is truncated. Under the old is_new gate every subsequent write saw
    is_new=False and the orphans stayed dark forever."""
    pytest.importorskip("core.learning.learning_store")
    from core.learning.learning_store import LearningStore
    from core.foundation.store import FileStore
    s = LearningStore(store=FileStore())
    for n in ("orphan_a", "orphan_b", "orphan_c"):
        _record(s, n)
    s.store.delete(INDEX)                      # the harmonize-shaped truncation
    _record(s, "written_after_the_loss")       # ANY write must restore membership
    idx = set(s.store.lrange(INDEX, 0, -1))
    for n in ("orphan_a", "orphan_b", "orphan_c"):
        assert n in idx, (
            f"{n} has a record but never returned to the index -- the write path is still "
            "self-sealing (is_new keyed on hash existence, not index membership)")


def test_p2_membership_equals_the_hash_plane():
    """The invariant, stated once: every discoverable record is a member. No exceptions,
    no anchor gate, no quality predicate -- membership is INTEGRITY, and filtering belongs
    to the surface (the settled claude/deepseek synthesis, round 2)."""
    from core.learning.learning_store import LearningStore
    from core.foundation.store import FileStore
    s = LearningStore(store=FileStore())
    for n in ("m_one", "m_two", "m_three"):
        _record(s, n)
    s.store.delete(INDEX)
    _record(s, "m_four")
    idx = set(s.store.lrange(INDEX, 0, -1))
    discovered = {k.split("learn:experiment:", 1)[1]
                  for k in s.store.keys("learn:experiment:*")
                  if "learn:experiment:" in k}
    assert discovered - idx == set(), f"records missing from the index: {discovered - idx}"


def test_p3_order_is_newest_first_by_record_timestamp():
    """The list's documented semantic (learning_store.py:19) is 'experiment ids, newest
    first'. Membership derives, but ORDER is the list's remaining job -- if the rebuild
    loses ordering it silently changes what every ranked read returns first."""
    from core.learning.learning_store import LearningStore
    from core.foundation.store import FileStore
    s = LearningStore(store=FileStore())
    _record(s, "older", timestamp="2026-01-01T00:00:00")
    _record(s, "newer", timestamp="2026-06-01T00:00:00")
    _record(s, "newest", timestamp="2026-12-01T00:00:00")
    idx = [i for i in s.store.lrange(INDEX, 0, -1) if i in ("older", "newer", "newest")]
    assert idx == ["newest", "newer", "older"], f"order not newest-first: {idx}"


def test_p4_a_record_the_rebuild_cannot_see_is_kept_not_dropped():
    """repair_learning_index.py's union-only guarantee, preserved in the derived rebuild:
    'a repair that can lose data is worse than the defect.' An index entry whose record is
    undiscoverable must survive the rebuild."""
    from core.learning.learning_store import LearningStore
    from core.foundation.store import FileStore
    s = LearningStore(store=FileStore())
    _record(s, "has_a_record")
    s.store.rpush(INDEX, "ghost_with_no_record")
    _record(s, "triggers_a_rebuild")
    idx = s.store.lrange(INDEX, 0, -1)
    assert "ghost_with_no_record" in idx, (
        "the rebuild dropped an index entry it could not resolve to a record -- union-only "
        "is the guarantee that makes an automatic rebuild safe to run unattended")


def test_p5_no_reader_sees_a_partial_index_during_rebuild():
    """Rebuild must not expose an empty window. Today's repair does DELETE+RPUSH; at 464
    the window is microseconds, but the hot path reads this list on EVERY tool call, so a
    reader landing mid-rebuild gets zero lessons and silently recalls nothing."""
    from core.learning.learning_store import LearningStore
    from core.foundation.store import FileStore
    s = LearningStore(store=FileStore())
    for i in range(5):
        _record(s, f"stable_{i}")
    seen = []
    real_delete = s.store.delete

    def watching_delete(*keys):
        if INDEX in keys:
            seen.append(len(s.store.lrange(INDEX, 0, -1)))
        return real_delete(*keys)

    s.store.delete = watching_delete
    try:
        _record(s, "one_more")
    finally:
        s.store.delete = real_delete
    assert s.store.lrange(INDEX, 0, -1), "index must be non-empty after a rebuild"


def test_p6_the_detector_is_wired_to_a_gate():
    """STRUCTURAL, and the whole reason this recurred. repair_learning_index.py --check has
    existed since 2026-07-25 explicitly 'to wire into ship gates', and was wired to nothing.
    The index was 434 after that repair and 16 two days later, silently. A detector nobody
    runs is not a detector (W69)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hook = os.path.join(root, "scripts", "githooks", "pre-push")
    assert os.path.isfile(hook), "pre-push gate missing"
    src = open(hook, encoding="utf-8").read()
    assert "repair_learning_index" in src, (
        "the lesson-index detector is not wired to the blocking gate -- this defect has "
        "already recurred once behind an unwired --check")


def test_p7_the_one_time_migration_cannot_run_by_accident():
    """harmonize_knowledge.py is a ONE-TIME 2026-06-20 migration whose phase_rebuild does
    `for k in r.keys('*'): if k not in canonical_keys: r.delete(k)` and then rewrites this
    index from a HARDCODED set of six. The six survivors in tonight's live index were all
    dated 2026-06-17 and are exactly that set. Prime suspect; it must refuse to run without
    an explicit, loud override."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(root, "scripts", "harmonize_knowledge.py")
    if not os.path.isfile(p):
        pytest.skip("harmonize_knowledge.py already retired")
    src = open(p, encoding="utf-8").read()
    assert "AKASHIC_ALLOW_HARMONIZE" in src, (
        "a destructive one-time migration that rewrites the live lesson index from a "
        "hardcoded 6-record set is still runnable without an explicit override")
