"""RED pins for one production-owned Discord outbound pump.

The 2026-09-06 human-origin gpt-new acceptance message reached its bound Codex
thread and produced a causally linked Bifrost reply, but that reply appeared in
the global Discord channel.  A daemon from another checkout won the shared
short-lived pump election; its credential allowlist predated gpt-new, so the
directed reply silently fell through to the global path.

These pins require two independent corrections:

* a directed operator reply with no registered seat lane is a loud failure,
  never global ambient traffic; and
* the production Discord gateway holds the existing pump lease across beats,
  so heterogeneous seat daemons cannot take turns deciding delivery policy.
"""
from __future__ import annotations

from pathlib import Path

from core.comm import discord_feed as feed
from core.outcome import BoundaryOutcome


class _Client:
    def __init__(self):
        self.streams = {
            "bifrost:broadcast": [],
            "bifrost:inbox:daniil": [
                ("100-0", {"frm": "sol", "to": "daniil", "kind": "reply",
                           "content": '"old"'}),
            ],
        }
        self.hash = {}

    def hgetall(self, key):
        return dict(self.hash)

    def hset(self, key, field, value):
        self.hash[field] = value

    def xrevrange(self, key, count=1):
        return list(reversed(self.streams.get(key, [])))[:count]

    def xrange(self, key, min="-", count=100):
        rows = self.streams.get(key, [])
        if min.startswith("("):
            floor = min[1:]
            return [row for row in rows if row[0] > floor][:count]
        return rows[:count]


class _Bus:
    ns = "bifrost"

    def __init__(self):
        self._client = _Client()

    def known_agents(self):
        return []

    def _inbox_key(self, agent):
        return f"bifrost:inbox:{agent}"


def test_missing_directed_seat_lane_refuses_instead_of_leaking_global(monkeypatch):
    bus = _Bus()
    monkeypatch.setattr(feed, "configured", lambda: True)
    monkeypatch.setattr(feed.DB, "should_forward", lambda msg: True)
    monkeypatch.setattr(feed, "seat_channel_url", lambda agent: "")
    failures = []
    monkeypatch.setattr(
        feed,
        "_post_failure_loud",
        lambda path, msg, mid, exc: failures.append((path, mid, str(exc))),
    )

    feed.pump(bus, post=lambda msg: None, room_post=lambda msg: None)
    bus._client.streams["bifrost:inbox:daniil"].append(
        ("101-0", {"frm": "gpt-new", "to": "daniil", "kind": "reply",
                   "content": '"causal answer"'}))
    global_calls = []
    room_calls = []
    out = feed.pump(
        bus,
        post=lambda msg: global_calls.append(msg),
        room_post=lambda msg: room_calls.append(msg),
    )

    assert not global_calls and not room_calls, (
        "a directed reply with no seat lane must never become global ambient mail"
    )
    assert out.detail["failed"] == 1 and out.detail["forwarded"] == 0
    assert failures and failures[0][0] == "seat-route"
    assert bus._client.hash["bifrost:inbox:daniil"] == "101-0", (
        "the display cursor still advances after a loud refusal; no retry storm"
    )


def test_persistent_owner_holds_one_token_across_pump_beats(monkeypatch):
    from core.comm import runner_lock

    acquired = []
    heartbeats = []
    released = []
    pumped = []
    monkeypatch.setattr(runner_lock, "instance_token", lambda key: "stable-owner-token")
    monkeypatch.setattr(
        runner_lock,
        "acquire",
        lambda key, token, ttl=None: acquired.append((key, token, ttl)) or True,
    )
    monkeypatch.setattr(
        runner_lock,
        "heartbeat",
        lambda key, token, ttl=None: heartbeats.append((key, token, ttl)) or True,
    )
    monkeypatch.setattr(
        runner_lock,
        "release",
        lambda key, token: released.append((key, token)) or True,
    )
    monkeypatch.setattr(
        feed,
        "pump",
        lambda bus: pumped.append(bus) or BoundaryOutcome.done(ref="pumped"),
    )

    bus = object()
    owner = feed.OutboundFeedOwner(bus, ttl=30)
    assert owner.beat().ok
    assert owner.beat().ok
    assert acquired == [("discord-pump", "stable-owner-token", 30)]
    assert len(heartbeats) >= 1
    assert pumped == [bus, bus]
    assert released == [], "ownership spans beats rather than rotating by daemon"

    owner.close()
    assert released == [("discord-pump", "stable-owner-token")]


def test_gateway_wires_and_releases_the_persistent_outbound_owner():
    source = (
        Path(__file__).resolve().parents[1] / "scripts" / "bifrost_runner_discord.py"
    ).read_text(encoding="utf-8")

    assert "OutboundFeedOwner(bus" in source
    assert "asyncio.create_task(_outbound_feed_loop())" in source
    assert "_outbound_owner.keepalive()" in source
    assert "_outbound_owner.close()" in source
