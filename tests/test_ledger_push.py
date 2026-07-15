"""
P3 / T023 -- ledger_update push: every transition rings the doorbell; nothing wakes on it.

Bar: each conductor verb broadcasts kind=ledger_update with the right to-status (done also
keeps its resolved marker); a bus failure never blocks a transition; and the wake listener
treats ledger control-plane kinds as skip (they insta-woke armed watchers 3x on 2026-07-09
-- the wake report prints the full read-state-first ledger anyway).

Run: py -m pytest tests/test_ledger_push.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import conductor


def _capture(monkeypatch):
    sent = []
    monkeypatch.setattr(conductor, "_broadcast",
                        lambda kind, text, meta: sent.append((kind, text, meta)))
    return sent


def _lifecycle(tmp_path, monkeypatch):
    sent = _capture(monkeypatch)
    path = str(tmp_path / "tasks.json")
    t = conductor.propose("P3 drill task", by="claude", client=None, path=path)
    tid = t["id"]
    conductor.approve(tid, by="user", client=None, path=path)
    conductor.claim(tid, "claude", client=None, path=path)
    conductor.start(tid, by="claude", client=None, path=path)
    conductor.verify(tid, by="claude", client=None, path=path)
    conductor.done(tid, "abc1234", "pytest", by="claude", client=None, path=path)
    return tid, sent


def test_every_transition_emits_ledger_update_with_from_state(tmp_path, monkeypatch):
    """The fold spec made the FROM-state load-bearing (a claim, a gate pass and a completion
    demand different reactions): every hint carries frm->to derived from ledger history."""
    tid, sent = _lifecycle(tmp_path, monkeypatch)
    arrows = [(m.get("frm_status"), m.get("to")) for k, _, m in sent if k == "ledger_update"]
    assert arrows == [("new", "proposed"), ("proposed", "approved"),
                      ("approved", "claimed"), ("claimed", "in_progress"),
                      ("in_progress", "verifying"), ("verifying", "done")]
    assert all(m.get("task") == tid for k, _, m in sent if k == "ledger_update")
    for k, txt, m in sent:
        if k == "ledger_update":
            assert f"LEDGER {tid} {m['frm_status']}->{m['to']}: " in txt, txt


def test_done_keeps_the_resolved_marker_too(tmp_path, monkeypatch):
    tid, sent = _lifecycle(tmp_path, monkeypatch)
    kinds = [k for k, _, _ in sent]
    assert "resolved" in kinds, "existing consumers keep their marker"
    resolved = next(txt for k, txt, _ in sent if k == "resolved")
    assert f"RESOLVED {tid}" in resolved and "do not redo" in resolved


def test_block_emits_blocked(tmp_path, monkeypatch):
    sent = _capture(monkeypatch)
    path = str(tmp_path / "tasks.json")
    t = conductor.propose("blockable", by="claude", client=None, path=path)
    conductor.approve(t["id"], by="user", client=None, path=path)
    conductor.claim(t["id"], "claude", client=None, path=path)
    conductor.start(t["id"], by="claude", client=None, path=path)   # block needs an ACTIVE task
    conductor.block(t["id"], "waiting on review", by="claude", client=None, path=path)
    assert ("ledger_update", "blocked") in [(k, m.get("to")) for k, _, m in sent]


def test_bus_failure_never_blocks_a_transition(tmp_path, monkeypatch):
    def _boom(kind, text, meta):
        raise RuntimeError("bus down")
    monkeypatch.setattr(conductor, "_broadcast", _boom)
    path = str(tmp_path / "tasks.json")
    t = conductor.propose("bus-down task", by="claude", client=None, path=path)
    assert t["id"], "transition succeeds while the doorbell is dead"
    assert conductor.approve(t["id"], by="user", client=None, path=path)["status"] == "approved"


# ---------------------------------------------------------- wake side (redis-backed)
def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def test_watch_stays_quiet_through_ledger_markers(capsys):
    from core.comm.bus import Bus
    from core.comm.bifrost_api import BifrostAPI
    import scripts.bifrost_wake as bw
    c = _client()
    ns = f"bifrost_test_{uuid.uuid4().hex[:8]}"
    try:
        a = Bus("alice", c, namespace=ns)
        api = BifrostAPI("bob")
        api.bus = Bus("bob", c, namespace=ns)
        a.send("bob", "chat", "prime")
        assert [m.content for m in api.bus.inbox(advance=True)] == ["prime"]
        a.broadcast("resolved", "RESOLVED T999: something -- CLOSED, do not redo.")
        a.broadcast("ledger_update", "LEDGER T999 -> done: something")
        rc = bw.watch("bob", 2, 400, api=api)
        out = capsys.readouterr().out.lower()
        # T073 Phase 3 renamed the benign deadline exit's provenance word:
        # 'quiet' -> 'self-cycle' (near-deadline chunk exit + re-arm trigger).
        # The semantic pinned HERE is unchanged and now asserted directly:
        # the watcher SAW both markers and still ended benign, not woken.
        assert rc == 0 and ("self-cycle" in out or "quiet" in out), \
            "ledger control-plane markers must never wake an armed watcher"
        assert "alice:resolved" in out and "alice:ledger_update" in out, \
            "the benign exit's provenance must show it sat THROUGH the markers"
    finally:
        keys = c.keys(f"{ns}:*")
        if keys:
            c.delete(*keys)
