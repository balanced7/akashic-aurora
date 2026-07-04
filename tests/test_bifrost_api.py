"""bifrost.api -- the one-door agent interface over the Bifrost bus (core/comm/bifrost_api).

Bar: the facade delegates honestly to the underlying primitives -- send/broadcast reach a peer's inbox
and the broadcast stream, inbox reads them back, presence registers, and the wake_cmd is the arm
string. Redis-backed in a throwaway namespace; skips if Redis is down. Also verifies fail-open shape
offline. Run: py -m pytest tests/test_bifrost_api.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bifrost_api import BifrostAPI


def _online_or_skip(api):
    if not api.online_now:
        pytest.skip("redis not available")


def test_send_lands_in_peer_inbox_stream():
    a = f"api-a-{uuid.uuid4().hex[:6]}"
    b = f"api-b-{uuid.uuid4().hex[:6]}"
    api_a = BifrostAPI(a)
    _online_or_skip(api_a)
    mid = api_a.send(b, "hello from a", kind="chat")
    assert mid                                            # got a message id (delegation happened)
    c = api_a.bus._client
    entries = c.xrevrange(f"bifrost:inbox:{b}", "+", "-", count=5) or []
    try:
        assert any(f.get("frm") == a and "hello from a" in str(f.get("content", "")) for _, f in entries)
    finally:
        for k in (c.keys(f"bifrost:inbox:{b}") or []):
            c.delete(k)


def test_broadcast_lands_on_broadcast_stream():
    a = f"api-bc-{uuid.uuid4().hex[:6]}"
    api_a = BifrostAPI(a)
    _online_or_skip(api_a)
    marker = f"ping-{uuid.uuid4().hex[:8]}"
    mid = api_a.broadcast(marker)
    assert mid
    c = api_a.bus._client
    entries = c.xrevrange("bifrost:broadcast", "+", "-", count=5) or []
    assert any(marker in str(f.get("content", "")) for _, f in entries)


def test_presence_and_who():
    a = f"api-p-{uuid.uuid4().hex[:6]}"
    api = BifrostAPI(a)
    _online_or_skip(api)
    assert api.online() is True
    assert any(p.get("agent") == a for p in api.who())


def test_wake_cmd_is_the_arm_string():
    api = BifrostAPI("claude")
    assert api.wake_cmd == "py scripts/bifrost_wake.py --agent claude"


def test_coordination_intent_lifecycle():
    """The coordination methods delegate to core.coord.intent: declare -> influence map -> covers -> release."""
    a = f"api-c-{uuid.uuid4().hex[:6]}"
    api = BifrostAPI(a)
    _online_or_skip(api)
    try:
        assert api.declare("build-feature-x", scope=["pkg/foo.py"])["ok"] is True
        assert any(i.get("agent") == a for i in api.intents(mine_only=True))
        assert api.covers("pkg/foo.py") is True
        assert api.covers("other/bar.py") is False
    finally:
        assert api.release_intent("build-feature-x") is True


def test_coordination_plan_gives_verdict():
    a = f"api-p-{uuid.uuid4().hex[:6]}"
    api = BifrostAPI(a)
    _online_or_skip(api)
    r = api.plan("do a thing", scope=["pkg/baz.py"], intent="do-a-thing")
    assert isinstance(r, dict)
    assert api.round_state().get("verdict") in ("green", "amber", "red")


def test_fail_open_offline(monkeypatch):
    api = BifrostAPI("x")
    monkeypatch.setattr(api.bus, "_client", None)         # force offline
    assert api.send("y", "hi") is None                    # degrades to None, no exception
    assert api.broadcast("hi") is None
    assert api.inbox() == []
    assert api.online() is False
