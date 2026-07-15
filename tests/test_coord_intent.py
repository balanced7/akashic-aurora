"""
Intent declaration (core/coord/intent) -- Policy 0.

Bar: an agent declaring a free intent is ADMITTED; a peer declaring the SAME intent YIELDS (duplicate
waste); a peer declaring a DIFFERENT intent proceeds even on the same files (the parallel-useful win
over file locks); re-declaring your own is a re-entrant refresh; scope `covers` a path by prefix;
fail-open when Redis is down. Redis-backed but isolated to throwaway agent ids + cleaned up. Skips if
Redis is down. Run: py -m pytest tests/test_coord_intent.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import intent as I


@pytest.fixture
def agents(monkeypatch):
    """Two throwaway agent ids in an ISOLATED drill namespace, + full ns cleanup.

    Repaired 2026-07-15: the 07-12 ns-isolation refactor renamed INTENT_PREFIX ->
    _intent_prefix() (per-call env read) and this fixture was missed -- teardown
    AttributeError'd on every test, cleanup never ran, and leaked tA-*/tB-* intents
    in the LIVE namespace poisoned the conflict asserts. Namespace isolation makes
    that class structurally impossible here (T039 test-* discipline)."""
    if I._client() is None:
        pytest.skip("redis not available")
    monkeypatch.setenv("BIFROST_NAMESPACE", f"t-intent-{uuid.uuid4().hex[:6]}")
    a, b = f"tA-{uuid.uuid4().hex[:6]}", f"tB-{uuid.uuid4().hex[:6]}"
    yield a, b
    c = I._client()
    for k in (c.keys(f"{I._intent_prefix()}*") or []):
        c.delete(k)


def test_free_intent_is_admitted(agents):
    a, _ = agents
    r = I.declare(a, "add rate limiting", scope=["api.py"])
    assert r["ok"] is True
    assert any(x["agent"] == a for x in I.active(agent=a))


def test_same_intent_by_peer_yields(agents):
    a, b = agents
    I.declare(a, "add rate limiting", scope=["api.py"])
    r = I.declare(b, "Add-Rate-Limiting", scope=["api.py"])         # same tag (normalized) -> duplicate
    assert r["ok"] is False
    assert a in {c["agent"] for c in r["conflicts"]}
    assert "coordinate" in r["reason"].lower()


def test_different_intent_same_file_proceeds(agents):
    """The parallel-useful win a file lock would block: same file, different intent -> both admitted."""
    a, b = agents
    assert I.declare(a, "restyle composer", scope=["ui.py"])["ok"] is True
    assert I.declare(b, "add hint cards", scope=["ui.py"])["ok"] is True    # same file, different intent
    tags = {I.slug(x["intent"]) for x in I.active()}
    assert {"restyle-composer", "add-hint-cards"} <= tags


def test_reentrant_refresh(agents):
    a, _ = agents
    assert I.declare(a, "build intent")["ok"] is True
    assert I.declare(a, "build intent")["ok"] is True               # same agent, same intent -> refresh


def test_release(agents):
    a, _ = agents
    I.declare(a, "temp intent")
    assert I.release(a, "temp intent") is True
    assert not any(I.slug(x["intent"]) == "temp-intent" for x in I.active(agent=a))


def test_covers_by_scope_prefix(agents):
    a, _ = agents
    I.declare(a, "coordination work", scope=["core/coord/"])
    assert I.covers(a, "core/coord/intent.py") is True
    assert I.covers(a, "scripts/bifrost_ui.py") is False


def test_fail_open_offline(monkeypatch):
    monkeypatch.setattr(I, "_client", lambda: None)
    assert I.declare("x", "anything")["ok"] is True                 # never wedge a local agent
    assert I.active() == [] and I.conflicts("x", "y") == []
