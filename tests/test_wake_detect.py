"""
P0 / T017 -- wake listener: detect, don't consume (the T016 Exhibit A regression pins).

Bar: a wake watcher NEVER moves the shared cursor. Skip-kind mail returns to the watcher
once (local cursor -- no busy-spin) yet remains fully consumable by the real reader.
A directed kind=reply arriving while a watcher runs must still appear to bifrost-sync/inbox
afterwards -- the exact scenario that silently ate a fenced report on 2026-07-09.

Design: docs/p0-wake-detect-design-2026-07.md. Redis-backed (skip if down).
Run: py -m pytest tests/test_wake_detect.py -q
"""
import os
import sys
import threading
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus
from core.comm.bifrost_api import BifrostAPI


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_test_{uuid.uuid4().hex[:8]}"


def _cleanup(c, ns):
    keys = c.keys(f"{ns}:*")
    if keys:
        c.delete(*keys)


def _api(agent, c, ns):
    """A BifrostAPI whose bus lives in a throwaway namespace (test isolation)."""
    api = BifrostAPI(agent)
    api.bus = Bus(agent, c, namespace=ns)
    return api


def _prime(sender_bus, api):
    """Establish a real shared cursor for api's agent (consume one priming message).

    Production agents always have a cursor; a VIRGIN cursor makes wake_block seed at "$"
    (tail -- deepseek red-team F1: a "0" seed would replay the whole stream), which would
    hide pre-queued test mail. Priming mirrors the real deployment."""
    sender_bus.send(api.agent, "chat", "prime")
    assert [m.content for m in api.bus.inbox(advance=True)] == ["prime"]


def _cursor_key(ns, agent):
    return f"{ns}:cursor:{agent}"


# ---------------------------------------------------------------- T1: wait(since=...)
def test_wait_since_reads_from_local_position_and_never_writes_shared_cursor():
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        b = Bus("bob", c, namespace=ns)
        first = a.send("bob", "chat", "one")
        a.send("bob", "chat", "two")
        got = b.wait(timeout_ms=1500, since={"inbox": first, "bc": "0"})
        assert [m.content for m in got] == ["two"], "since=<id of one> must yield only later entries"
        assert not c.exists(_cursor_key(ns, "bob")), "a since-read must never create/write the shared cursor"
        # default-path read still sees BOTH (shared cursor untouched)
        assert [m.content for m in b.inbox(advance=False)] == ["one", "two"]
    finally:
        _cleanup(c, ns)


def test_bus_cursor_is_a_read_only_snapshot():
    c, ns = _client(), _ns()
    try:
        b = Bus("bob", c, namespace=ns)
        cur = b.cursor()
        assert set(cur) == {"inbox", "bc"}
        assert not c.exists(_cursor_key(ns, "bob")), "cursor() must not materialize the key"
    finally:
        _cleanup(c, ns)


# ------------------------------------------------- T2: the Exhibit A regression pin
def test_wake_block_returns_skip_kind_once_and_leaves_it_consumable():
    """The pin for T016 Exhibit A: a kind=reply seen by a watcher must (a) not busy-spin,
    (b) never advance the shared cursor, (c) still reach the real consumer afterwards."""
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)
        _prime(a, api)
        cursor_after_prime = c.hgetall(_cursor_key(ns, "bob"))
        a.send("bob", "reply", "the fenced report")
        got1 = api.wake_block(timeout_ms=1500)
        assert [m.content for m in got1] == ["the fenced report"], "first wake_block detects it"
        t0 = time.time()
        got2 = api.wake_block(timeout_ms=700)
        assert got2 == [], "second wake_block must NOT re-return it (local cursor advanced; no spin)"
        assert time.time() - t0 >= 0.5, "second call must BLOCK (not hot-return the same entry)"
        assert c.hgetall(_cursor_key(ns, "bob")) == cursor_after_prime, \
            "shared cursor untouched by wake_block"
        assert [m.content for m in api.bus.inbox()] == ["the fenced report"], \
            "the real consumer still receives the reply (THE regression)"
    finally:
        _cleanup(c, ns)


def test_wake_block_wake_worthy_is_detected_and_still_consumable():
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)
        _prime(a, api)
        a.send("bob", "chat", "wake up")
        got = api.wake_block(timeout_ms=1500)
        assert [m.content for m in got] == ["wake up"]
        assert [m.content for m in api.bus.inbox()] == ["wake up"], "detected, not consumed"
    finally:
        _cleanup(c, ns)


def test_wake_block_local_cursor_spans_inbox_and_broadcast():
    """Stream asymmetry: local tracking must advance per-stream (m.to=='*' vs direct)."""
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)
        _prime(a, api)
        a.send("bob", "reply", "direct-skip")
        a.broadcast("trace", "bc-skip")
        got1 = api.wake_block(timeout_ms=1500)
        assert sorted(m.content for m in got1) == ["bc-skip", "direct-skip"]
        assert api.wake_block(timeout_ms=600) == [], "neither stream re-delivers to the watcher"
        assert sorted(m.content for m in api.bus.inbox()) == ["bc-skip", "direct-skip"], \
            "both remain unread for the real consumer"
    finally:
        _cleanup(c, ns)


# ------------------------------------------------------------- T4: watch() semantics
def _watch(agent, api, deadline_s, block_ms):
    import scripts.bifrost_wake as bw
    return bw.watch(agent, deadline_s, block_ms, api=api)


def test_watch_keeps_waiting_through_trace_and_exits_quiet(capsys):
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)
        _prime(a, api)
        a.broadcast("trace", "noise 1")
        rc = _watch("bob", api, deadline_s=2, block_ms=400)
        assert rc == 0
        out = capsys.readouterr().out
        assert "quiet" in out.lower(), "trace alone must not read as a wake"
        assert [m.content for m in api.bus.inbox()] == ["noise 1"], "trace still consumable"
    finally:
        _cleanup(c, ns)


def test_watch_exits_on_chat_without_consuming(capsys):
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)
        _prime(a, api)
        a.send("bob", "chat", "real directive")
        rc = _watch("bob", api, deadline_s=6, block_ms=400)
        assert rc == 0
        assert "real directive" in capsys.readouterr().out
        assert [m.content for m in api.bus.inbox()] == ["real directive"], "wake did not consume"
    finally:
        _cleanup(c, ns)


def test_watch_exits_on_reply_new_semantics(capsys):
    """P0 semantics change: a directed reply wakes the idle agent (T016: the eaten report
    was a reply the sleeping agent had explicitly requested)."""
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)
        _prime(a, api)
        a.send("bob", "reply", "your requested report")
        rc = _watch("bob", api, deadline_s=6, block_ms=400)
        assert rc == 0
        assert "your requested report" in capsys.readouterr().out
        assert [m.content for m in api.bus.inbox()] == ["your requested report"]
    finally:
        _cleanup(c, ns)


def test_watch_skips_own_broadcasts_without_spin():
    """An agent's own broadcast is filtered from delivery -- the watcher must pass it by
    on the LOCAL cursor (the claude-review class from T014: filtered != truncated)."""
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)
        _prime(a, api)
        api.bus.broadcast("inform", "my own announcement")
        t0 = time.time()
        rc = _watch("bob", api, deadline_s=2, block_ms=400)
        assert rc == 0 and time.time() - t0 >= 1.5, "own broadcast must not wake or spin"
    finally:
        _cleanup(c, ns)


# --------------------------------------------- review fold-ins (deepseek red-team F1/F2/F5)
def test_wake_block_virgin_cursor_seeds_at_tail_not_zero():
    """F1/F10: an agent that has never consumed (or whose cursor read failed) must NOT replay
    the whole stream as 'new' -- backlog stays invisible; only post-arm mail wakes."""
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)                 # NO prime: virgin cursor
        a.send("bob", "chat", "ancient backlog")
        assert api.wake_block(timeout_ms=400) == [], "virgin seed = $: backlog must not wake"
        a.send("bob", "chat", "fresh mail")
        got = api.wake_block(timeout_ms=1500)
        assert [m.content for m in got] == ["fresh mail"]
        assert sorted(m.content for m in api.bus.inbox()) == ["ancient backlog", "fresh mail"], \
            "nothing consumed either way"
    finally:
        _cleanup(c, ns)


def test_wake_block_fast_forwards_past_live_consumed_mail():
    """F1 concurrency: mail a live session consumed while the watcher blocked must not wake
    the watcher afterwards (local cursor lifts to the shared cursor every call)."""
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)
        _prime(a, api)
        assert api.wake_block(timeout_ms=300) == []          # seed the local cursor
        a.send("bob", "chat", "handled by the live session")
        assert [m.content for m in api.bus.inbox(advance=True)] == ["handled by the live session"]
        t0 = time.time()
        assert api.wake_block(timeout_ms=700) == [], \
            "consumed mail must not wake the watcher (fast-forward to shared cursor)"
        assert time.time() - t0 >= 0.5, "must block, not hot-return the consumed entry"
    finally:
        _cleanup(c, ns)


def test_watch_ignores_broadcast_reply_but_wakes_on_directed_reply(capsys):
    """F5: a BROADCAST reply is room chatter -- no wake; a DIRECTED reply wakes."""
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        api = _api("bob", c, ns)
        _prime(a, api)
        a.broadcast("reply", "room-wide answer")
        rc = _watch("bob", api, deadline_s=2, block_ms=400)
        assert rc == 0 and "quiet" in capsys.readouterr().out.lower(), \
            "broadcast reply must not wake"
        a.send("bob", "reply", "answer for bob")
        rc = _watch("bob", api, deadline_s=6, block_ms=400)
        assert rc == 0 and "answer for bob" in capsys.readouterr().out
    finally:
        _cleanup(c, ns)


def test_wake_block_survives_stream_trimming_with_bounded_paging():
    """F2: a local cursor pointing below the trimmed stream head must degrade to bounded
    paging (no error, terminates, later mail still detected) -- never an endless storm."""
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns, maxlen=50)
        api = _api("bob", c, ns)
        api.bus.maxlen = 50
        _prime(a, api)
        assert api.wake_block(timeout_ms=300) == []          # seed at the pre-flood frontier
        for i in range(300):                                 # flood past maxlen -> head trimmed
            a.send("bob", "trace", f"noise {i}")
        pages = 0
        while api.wake_block(timeout_ms=250) and pages < 40:
            pages += 1
        assert pages < 40, "paging must terminate (local cursor advances past the flood)"
        a.send("bob", "chat", "after the flood")
        got = api.wake_block(timeout_ms=1500)
        assert [m.content for m in got] == ["after the flood"], "detection works after trimming"
    finally:
        _cleanup(c, ns)


# ------------------------------------------------------------- T5: singleton stand-down
def test_watch_stands_down_when_heartbeat_stolen(tmp_path):
    c, ns = _client(), _ns()
    try:
        api = _api("bob", c, ns)
        hb = tmp_path / "bifrost_wake_bob.pid"
        hb.write_text(str(os.getpid()))          # a DIFFERENT live pid owns the seat
        import scripts.bifrost_wake as bw
        t0 = time.time()
        rc = bw.watch("bob", 30, 400, api=api, hb_path=str(hb), my_pid=999999)
        assert rc == 0, ("stolen seat -> stand down BENIGN, exit 0 (Wave 2: a nonzero exit "
                         "badges a FAILED task into a live session; provenance is the printed line)")
        assert time.time() - t0 < 5, "stand-down must be prompt, not deadline-length"
    finally:
        _cleanup(c, ns)
