"""Bifrost Mesh W1 (doorbell) + W2 (dispatcher triage).

Hermetic: a fake Redis for the doorbell publish path, injected peek/invoker for the dispatcher
triage. No canonical Redis, no real pub/sub.

Run: py -m pytest tests/test_bifrost_mesh.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus, bell_channel
from core.comm.dispatcher import Dispatcher, should_escalate


class FakeRedis:
    """Just enough for Bus._emit/_ring_bell/_touch. Records publishes; can simulate a bell failure."""
    def __init__(self, publish_raises=False):
        self.published, self.streams, self._n, self._raise = [], {}, 0, publish_raises

    def xadd(self, stream, env, maxlen=None, approximate=True):
        self._n += 1
        mid = f"{self._n}-0"
        self.streams.setdefault(stream, []).append((mid, env))
        return mid

    def publish(self, channel, data):
        if self._raise:
            raise RuntimeError("pubsub down")
        self.published.append((channel, data))
        return 1

    def set(self, *a, **k):
        return True


# ----------------------------------------------------------------- W1 doorbell
def test_send_rings_the_doorbell_for_recipient():
    fake = FakeRedis()
    mid = Bus("alice", client=fake).send("bob", "request", "hi")
    assert mid is not None and fake.published
    ch, data = fake.published[-1]
    assert ch == bell_channel("bob")
    notice = json.loads(data)
    assert notice == {"mid": mid, "frm": "alice", "to": "bob", "kind": "request"}


def test_broadcast_rings_the_star_channel():
    fake = FakeRedis()
    Bus("alice", client=fake).broadcast("announce", "hi")
    assert fake.published[-1][0] == bell_channel("*")


def test_doorbell_is_lose_safe():
    # a failed bell must NOT fail the send -- the Stream is the durable truth
    fake = FakeRedis(publish_raises=True)
    mid = Bus("alice", client=fake).send("bob", "note", "hi")
    assert mid is not None
    assert fake.streams  # the message was still XADDed


# ----------------------------------------------------------------- W2 dispatcher triage
def _disp(agents, invoker_ret=True):
    calls = []

    def invoker(agent, digest, notice):
        calls.append((agent, digest, notice))
        return invoker_ret

    return Dispatcher(agents, invoker=invoker, peek=lambda a: [f"digest:{a}"]), calls


def test_escalation_gate():
    assert should_escalate({"kind": "request"}) is True
    assert should_escalate({"kind": "handoff"}) is True
    assert should_escalate({"kind": "note"}) is False
    assert should_escalate({"kind": "chat", "importance": "high"}) is True  # importance overrides kind


def test_actionable_kind_wakes_target():
    d, calls = _disp({"claude", "cursor"})
    res = d.handle_notice({"frm": "cursor", "to": "claude", "kind": "request"})
    assert res["escalated"] and res["results"][0] == {"agent": "claude", "escalated": True,
                                                       "dispatched": True, "digest": ["digest:claude"]}
    assert calls and calls[0][0] == "claude"


def test_note_does_not_wake():
    d, calls = _disp({"claude"})
    res = d.handle_notice({"frm": "cursor", "to": "claude", "kind": "note"})
    assert res["escalated"] is False
    assert res["results"][0]["dispatched"] is False and not calls   # low-token: seen on next boot


def test_unmanaged_recipient_ignored():
    d, calls = _disp({"claude"})
    res = d.handle_notice({"frm": "x", "to": "nobody-here", "kind": "request"})
    assert res["results"] == [] and not calls


def test_broadcast_wakes_all_but_sender():
    d, calls = _disp({"claude", "cursor", "gemini"})
    res = d.handle_notice({"frm": "cursor", "to": "*", "kind": "handoff"})
    assert {r["agent"] for r in res["results"]} == {"claude", "gemini"}   # sender excluded
    assert {c[0] for c in calls} == {"claude", "gemini"}
