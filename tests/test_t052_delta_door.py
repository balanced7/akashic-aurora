"""T052 (R1 delta door) PRE-REGISTERED ACCEPTANCE -- committed RED before implementation.

Cites research/reviewed/r1-delta-door-reconciliation-2026-07-14.md (the build spec;
deepseek confirm: research/reviewed/deepseek-r1-reconciliation-confirm-2026-07-14.md).
Tier: FENCE-LITE (recorded at registration; deepseek confirmed; he reviews the build).

REGISTERED SEAM (agent/harness/delta.py):
  * current_positions(agent) -> {git_commit, ledger_seq, notes_head, promoted_id}
    (each field independently fail-soft; "?" on error, never raises)
  * DeltaMark(agent): .read() -> dict|None ; .write(positions)
  * delta_boot_block(agent, budget=1200) -> (text, commit_fn) -- MARK-LAG CONTRACT:
    building the block NEVER writes the mark; the CALLER invokes commit_fn only after
    the context containing the block has been delivered (D1 ruling).
  * render_full(agent) -> str  (the `delta` verb; 30s render cache)

Pins (expected RED today -- the module does not exist):
  P1 mark-lag: delta_boot_block alone never writes the mark; commit_fn does.
  P2 newborn: no mark -> block == "" (full boot unchanged); after commit + movement,
     the second block renders the delta.
  P3 budget: an oversize render degrades LOUDLY to counts + pull pointer, <= budget.
  P4 backwards git: mark ahead of HEAD -> loud 'moved backwards' render, mark unmoved.
  P5 fail-soft: one broken source renders its (unavailable) line; others intact.
  P6 zero-cost silence: with a mark and NOTHING moved, the block is EXACTLY "" (the
     strongest boot-shrink guarantee; the live boot-shrink measure = M5 live-exercise).
  P7 ledger delta: a seq bump renders the ledger section with the movement.
  P8 render cache: two render_full calls within the TTL return the identical cached
     block even if a source moves between them.

Run: py -m pytest tests/test_t052_delta_door.py -q  (Redis pins skip when down)
"""
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _mod():
    import importlib
    try:
        return importlib.import_module("agent.harness.delta")
    except ImportError:
        pytest.fail("agent/harness/delta.py does not exist yet (RED by design)")


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _agent():
    return f"t052-{uuid.uuid4().hex[:8]}"


def _positions(git="aaa1111", seq="5", notes="n-1", promoted="p-1"):
    return {"git_commit": git, "ledger_seq": seq, "notes_head": notes, "promoted_id": promoted}


# ------------------------------------------------------------------ P1: mark-lag
def test_p1_block_never_writes_commit_fn_does(monkeypatch):
    _client()
    d = _mod()
    agent = _agent()
    text, commit = d.delta_boot_block(agent)
    assert d.DeltaMark(agent).read() is None, \
        "P1: building the block must NEVER write the mark (mark-lag, D1 ruling)"
    commit()
    assert d.DeltaMark(agent).read() is not None, "P1: commit_fn writes the mark"


# ------------------------------------------------------------------ P2: newborn
def test_p2_newborn_empty_then_delta_after_movement(monkeypatch):
    _client()
    d = _mod()
    agent = _agent()
    text, commit = d.delta_boot_block(agent)
    assert text == "", "P2: a newborn (no mark) gets NO delta block -- full boot unchanged"
    commit()
    # simulate movement: rewind the stored ledger_seq so current != mark
    mark = d.DeltaMark(agent)
    pos = mark.read()
    pos["ledger_seq"] = "-1"
    mark.write(pos)
    text2, _ = d.delta_boot_block(agent)
    assert text2 != "" and "ledger" in text2, \
        "P2: after the mark exists and a source moved, the block renders the delta"


# ------------------------------------------------------------------ P3: budget
def test_p3_oversize_render_degrades_loud_within_budget(monkeypatch):
    _client()
    d = _mod()
    agent = _agent()
    monkeypatch.setattr(d, "_git_log_range",
                        lambda a, b: [f"{i:07x} very long synthetic commit subject line "
                                      f"padding padding padding {i}" for i in range(400)],
                        raising=False)
    mark = d.DeltaMark(agent)
    pos = d.current_positions(agent)
    pos["git_commit"] = "0" * 7            # force a "moved" git range
    mark.write(pos)
    text, _ = d.delta_boot_block(agent, budget=1200)
    assert len(text) <= 1200, "P3: the block must fit its declared budget"
    assert "delta truncated" in text or "more" in text, \
        "P3: over-budget must degrade LOUDLY with a pull pointer (packet law)"


# ------------------------------------------------------------------ P4: backwards git
def test_p4_backwards_git_loud_and_mark_unmoved(monkeypatch):
    _client()
    d = _mod()
    agent = _agent()
    mark = d.DeltaMark(agent)
    pos = d.current_positions(agent)
    pos["git_commit"] = "f" * 40           # not an ancestor of HEAD -> backwards/diverged
    mark.write(pos)
    text, _ = d.delta_boot_block(agent)
    assert "backwards" in text.lower() or "diverged" in text.lower(), \
        "P4: backwards movement must render LOUD"
    assert d.DeltaMark(agent).read()["git_commit"] == "f" * 40, \
        "P4: the mark is never auto-reset on backwards movement"


# ------------------------------------------------------------------ P5: fail-soft
def test_p5_one_broken_source_does_not_blank_the_block(monkeypatch):
    _client()
    d = _mod()
    agent = _agent()
    mark = d.DeltaMark(agent)
    pos = d.current_positions(agent)
    pos["ledger_seq"] = "-1"               # ledger moved
    mark.write(pos)
    monkeypatch.setattr(d, "_notes_head",
                        lambda: (_ for _ in ()).throw(RuntimeError("notes store down")),
                        raising=False)
    text, _ = d.delta_boot_block(agent)
    assert "ledger" in text, "P5: healthy sources must still render"
    # the broken source either renders an unavailable line or drops out -- never raises
    assert isinstance(text, str)


# ------------------------------------------------------------------ P6: zero-cost silence
def test_p6_unmoved_world_renders_empty_block(monkeypatch):
    _client()
    d = _mod()
    agent = _agent()
    text, commit = d.delta_boot_block(agent)
    commit()                                # mark == current positions
    text2, _ = d.delta_boot_block(agent)
    assert text2 == "", \
        "P6: with a mark and nothing moved, the delta block is EXACTLY empty (zero cost)"


# ------------------------------------------------------------------ P7: ledger delta
def test_p7_seq_bump_renders_ledger_section(monkeypatch):
    _client()
    d = _mod()
    agent = _agent()
    _, commit = d.delta_boot_block(agent)
    commit()
    mark = d.DeltaMark(agent)
    pos = mark.read()
    try:
        pos["ledger_seq"] = str(int(pos["ledger_seq"]) - 3)
    except (TypeError, ValueError):
        pos["ledger_seq"] = "-3"
    mark.write(pos)
    text, _ = d.delta_boot_block(agent)
    assert "ledger" in text, "P7: a seq movement renders the ledger section"


# ------------------------------------------------------------------ P8: render cache
def test_p8_render_cache_within_ttl(monkeypatch):
    _client()
    d = _mod()
    agent = _agent()
    _, commit = d.delta_boot_block(agent)
    commit()
    first = d.render_full(agent)
    mark = d.DeltaMark(agent)
    pos = mark.read()
    pos["ledger_seq"] = "-9"               # a source moves AFTER the first render
    mark.write(pos)
    second = d.render_full(agent)
    assert second == first, \
        "P8: within the TTL the cached render returns -- identical block, movement unseen"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
