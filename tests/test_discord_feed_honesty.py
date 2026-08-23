"""
The feed must not lie about delivery (2026-08-23 incident pin).

Root cause, found by the vandor rescue sprout (state/spawn-logs/
spawn-1787516635.log) during the evening the operator read as "bifrost down":
pump()'s seat-lane branch swallowed webhook failures with a bare except,
advanced the cursor, AND counted the post as forwarded -- so every reply to
the operator could die silently while the feed reported success, including
the sprout's own answer about this very bug.

  P1  a failing seat-lane post is COUNTED (failed=1, forwarded=0), CONFESSED
      on stderr, and the outcome ref says so.
  P2  the cursor still advances: the next beat does NOT re-attempt the dead
      post (skip, never a retry storm) -- failure is loud exactly once.

Run: py -m pytest tests/test_discord_feed_honesty.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import discord_feed
from core.comm.bus import Bus


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST,
                                        port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3,
                                        decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def test_feed_confesses_dead_webhook_and_never_retries(monkeypatch, capsys):
    assert "daniil" in discord_feed._OPERATOR_INBOXES
    c = _client()
    ns = f"feedtest_{uuid.uuid4().hex[:8]}"
    cursor_key = f"{ns}:feed_cursor_test"
    monkeypatch.setattr(discord_feed, "CURSOR_KEY", cursor_key)
    monkeypatch.setattr(discord_feed, "configured", lambda: True)
    monkeypatch.setattr(discord_feed.DB, "should_forward", lambda m: True)
    monkeypatch.setattr(discord_feed.DB, "webhook_url", lambda: "http://x.invalid")
    monkeypatch.setattr(discord_feed, "seat_channel_url",
                        lambda frm: "http://lane.invalid")
    monkeypatch.setattr(discord_feed.ROOMS, "persona",
                        lambda f: {"username": "t", "avatar_url": ""})
    monkeypatch.setattr(discord_feed.ROOMS, "render_room_parts", lambda m: ["x"])

    def _dead_post(*a, **k):
        raise RuntimeError("webhook is a corpse")
    monkeypatch.setattr(discord_feed.ROOMS, "_default_post", _dead_post)

    bus = Bus("claude", client=c, namespace=ns, promote=False)
    try:
        discord_feed.pump(bus)                      # first contact: tail-init
        mid = bus.send("daniil", "reply", "the answer that must not vanish")
        assert mid

        out = discord_feed.pump(bus)
        ref = str(getattr(out, "ref", "") or out)
        assert "failed=1" in ref, f"the outcome must confess the death: {ref}"
        assert "forwarded=0" in ref, "a dead post must never count as forwarded"
        err = capsys.readouterr().err
        assert "POST FAILED" in err, "the confession must reach stderr"

        out2 = discord_feed.pump(bus)
        ref2 = str(getattr(out2, "ref", "") or out2)
        assert "failed=0" in ref2, (
            "the cursor advanced past the corpse -- no retry storm, "
            "loud exactly once")
    finally:
        keys = c.keys(f"{ns}:*")
        if keys:
            c.delete(*keys)
        c.delete(cursor_key)
