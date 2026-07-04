"""
A0.1 -- the environmental write-gate (core/comm/locks.guard_write).

Bar: an agent PROACTIVELY claims a free path (peers then auto-blocked), the claim is re-entrant
(refresh-on-activity, so a held lock never lapses mid-task), a peer YIELDS rather than clobbers, and
everything fails open when Redis is down. Uses throwaway paths so it never touches live file locks.
Skips if Redis is down. Run: py -m pytest tests/test_locks_guard_write.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import locks


@pytest.fixture
def path():
    """A unique throwaway path + guaranteed cleanup of any lock left on it. Skips if Redis is down."""
    if locks._connect() is None:
        pytest.skip("redis not available")
    p = f"tests/_guard_{uuid.uuid4().hex[:8]}.tmp"
    yield p
    for a in ("claude", "deepseek"):
        try:
            locks.LockManager(a).release(p)
        except Exception:
            pass


def test_first_writer_claims(path):
    g = locks.guard_write(path, "claude")
    assert g["ok"] is True and g["claimed"] is True
    assert g["held_by"] == "claude"


def test_reentrant_refresh(path):
    assert locks.guard_write(path, "claude")["ok"] is True
    again = locks.guard_write(path, "claude")            # same agent, second edit
    assert again["ok"] is True                            # re-entrant: keeps working, refreshes TTL
    assert again["held_by"] == "claude"


def test_peer_yields_not_clobbers(path):
    locks.guard_write(path, "claude")                     # claude claims it
    g = locks.guard_write(path, "deepseek")               # deepseek must yield
    assert g["ok"] is False and g["claimed"] is False
    assert g["held_by"] == "claude"
    assert "yield" in g["reason"].lower()


def test_influence_map_reflects_claim(path):
    locks.guard_write(path, "claude")
    assert (locks.LockManager("deepseek").holder(path) or {}).get("agent") == "claude"
    assert locks.path_conflict(path, "deepseek")["conflict"] is True     # the map shows the collision


def test_fail_open_offline(monkeypatch, path):
    monkeypatch.setattr(locks, "_connect", lambda: None)
    g = locks.guard_write(path, "deepseek")
    assert g["ok"] is True                                 # never wedge a local edit when the bus is down
