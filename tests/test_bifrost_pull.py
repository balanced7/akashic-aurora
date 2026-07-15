"""
Pull-side read lane: boot surfaces unread Bifrost inbox (non-consuming) + promoted() verb.

Run: py -m pytest tests/test_bifrost_pull.py -q
"""
import argparse
import io
import os
import sys
import uuid
from contextlib import redirect_stdout

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from agent import bifrost_pull
from core.comm.bus import Bus
from core.comm.promoter import PROMOTED_KIND


def test_format_digest_line_is_compact():
    line = bifrost_pull.format_digest_line(
        {"frm": "cursor", "kind": "handoff", "ts": "2026-06-28T22:43:55+00:00",
         "content": "x" * 500})
    assert "[handoff]" in line and "cursor>" in line and "22:43" in line
    assert "...[truncated]" in line          # long body is clipped, not dumped
    assert len(line) < 120                    # a cheap one-liner, not the full body


def _redis_client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_pull_{uuid.uuid4().hex[:8]}"


def _cleanup(client, ns):
    keys = client.keys(f"{ns}:*")
    if keys:
        client.delete(*keys)


def test_peek_does_not_advance_cursor():
    c = _redis_client()
    agent = f"alice_peek_{uuid.uuid4().hex[:6]}"
    sender = f"bob_peek_{uuid.uuid4().hex[:6]}"
    try:
        Bus(sender, c, promote=False).send(agent, "chat", "hello peek")
        cur_before = c.hgetall(f"bifrost:cursor:{agent}") or {}
        msgs = bifrost_pull.peek_inbox(agent, limit=30)
        cur_after = c.hgetall(f"bifrost:cursor:{agent}") or {}
        ours = [m for m in msgs if m.get("content") == "hello peek"]
        assert len(ours) == 1
        assert cur_before == cur_after, "peek must not advance cursor"
        got = Bus(agent, c, promote=False).inbox(limit=30, advance=True)
        assert any(getattr(m, "content", None) == "hello peek" for m in got)
    finally:
        for key in (f"bifrost:inbox:{agent}", f"bifrost:cursor:{agent}", f"bifrost:presence:{agent}"):
            c.delete(key)


def test_boot_prints_bifrost_section(monkeypatch):
    # T074-W13 (repaired 2026-07-15): primer-aware boot deliberately DROPS the
    # whisper-carried sections (UNREAD BIFROST among them) whenever a harness
    # session id is in env -- so running this suite inside a Claude session
    # flipped the mode out from under the assert. This pin means the FULL boot
    # contract; say so via the R13 hatch instead of inheriting ambient env.
    monkeypatch.setenv("AKASHIC_BOOT_FULL", "1")
    c = _redis_client()
    agent = f"cursor_pull_{uuid.uuid4().hex[:6]}"
    try:
        Bus("claude", c, promote=False).send(agent, "handoff", "pull-side test")
        buf = io.StringIO()
        with redirect_stdout(buf):
            agent_cli.cmd_boot(argparse.Namespace(agent_id=agent, task="test", json=False))
        out = buf.getvalue()
        assert "UNREAD BIFROST" in out
        assert "pull-side test" in out
    finally:
        for key in (f"bifrost:inbox:{agent}", f"bifrost:cursor:{agent}", f"bifrost:presence:{agent}"):
            c.delete(key)


def test_cmd_promoted_formatter():
    evs = [{
        "kind": PROMOTED_KIND,
        "at": "2026-06-28T22:00:00",
        "detail": {"frm": "claude", "to": "cursor", "kind": "handoff", "content": "durable handoff"},
        "_ref": "event:events:raw:test1",
    }]
    out = bifrost_pull.format_promoted_events(evs)
    assert "durable handoff" in out
    assert "event:events:raw:test1" in out


def test_bifrost_sync_peek():
    c = _redis_client()
    agent = f"cursor_sync_{uuid.uuid4().hex[:6]}"
    try:
        Bus("claude", c, promote=False).send(agent, "note", "sync test")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = agent_cli.cmd_bifrost_sync(
                argparse.Namespace(agent_id=agent, limit=5, consume=False, json=False))
        assert rc == 0
        assert "sync test" in buf.getvalue()
        still = bifrost_pull.peek_inbox(agent, limit=30)
        assert any(m.get("content") == "sync test" for m in still)
    finally:
        for key in (f"bifrost:inbox:{agent}", f"bifrost:cursor:{agent}", f"bifrost:presence:{agent}"):
            c.delete(key)
