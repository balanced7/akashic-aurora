"""Defer 224ac54766 -- the lane watcher's ARM-TIME PENDING CHECK must read the cursor
family this seat's consumer actually advances.

MEASURED 2026-09-07 on the live bus (read-only HGETALL/XRANGE, port 16379):

    bifrost:cursor:claude        inbox=1787969686471-0  (2026-08-29, gen 365)  LEGACY family
    bifrost:cursor:lane:claude   inbox=1788729020181-0  (2026-09-06, gen 368)  LANE family
    legacy inbox entries behind the legacy cursor: 204; the first five are kind=chat/reply

Every consumer in the house drains the LANE family (BIFROST_CONSUME_LANE=work is defaulted
in eight places) and nothing has advanced the legacy cursor since 08-29. Yet
BifrostAPI._wake_block_lane's arm-time pending check was `bus.wait(timeout_ms=1, limit=10)`
-- since=None, streams=None -- which reads the LEGACY cursor. So every fresh arm found ten
stale 08-29 chat/reply messages, called them "pending", and fired on mail the seat had drained
a week earlier. Only the per-session S0-gamma sidecar made a seat converge (the '2-3
insta-fire arms' in lesson wake_local_cursor_history_replay), and the defer counted five
band-aids in one session all patching one unnamed shared-resource co-tenant. The co-tenant
is the legacy cursor family nobody advances any more.

THE GUARANTEE THESE PINS STATE:
  * 'pending' means BEHIND THE LANE CURSOR the consumer commits, whenever this seat HAS a
    lane cursor (non-virgin lane hash). Mail the lane consumer already committed past is not
    pending, whatever the legacy cursor says; mail still behind the lane cursor IS pending,
    even if some legacy co-tenant swept the shared cursor past it (the lane consumer will
    redeliver it -- the watcher and the consumer must mean the same thing by "unread").
  * A VIRGIN lane hash means no lane consumer has ever run for this seat, so the legacy
    family remains the authority there: the T017 arm-onto-pending contract (t045 L4) and the
    migrant's unconsumed legacy backlog both still wake, unchanged.
  * The watcher stays DETECT-ONLY: the family choice is read from the lane hash, and neither
    cursor is written by detection (no lane_cursor_flip_init from the watcher).
  * The seed warning names the family it peeked, so its drain instruction points at the
    cursor that is actually behind.

Redis-backed pins use throwaway namespaces (skip if Redis is down); the first pin is a pure
seam pin on a fake bus. Run: py -m pytest tests/test_wake_lane_pending_reads_lane_cursor.py -q
"""
import logging
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm.bus import Bus  # noqa: E402
from core.comm.bifrost_api import BifrostAPI  # noqa: E402


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_d224_{uuid.uuid4().hex[:8]}"


def _lane_tail(c, key):
    last = c.xrevrange(key, count=1)
    return str(last[0][0]) if last else "0"


def _kinds(msgs):
    return [str(getattr(m, "kind", "?")) for m in msgs]


# ------------------------------------------------------------ 0: the seam, no Redis
class _Msg:
    def __init__(self, kind="chat", frm="kimi"):
        self.kind, self.frm = kind, frm
        self.ts, self.content, self.meta, self.to = "2026-08-29T02:14:00+00:00", "x", {}, "claude"


class _FamilyBus:
    """A fake bus with a NON-VIRGIN lane cursor at tail and a legacy cursor with stale
    wake-worthy mail behind it -- the live claude shape on 2026-09-07. Records which family
    the pending peek asked for."""

    def __init__(self):
        self.ns = "test"
        self.legacy_pending = [_Msg("chat"), _Msg("reply", frm="deepseek")]
        self.lane_cur = {"inbox": "1788729020181-0", "bc": "1788729038626-0",
                         "sig_inbox": "1788712362319-0", "sig_bc": "0",
                         "shadow_inbox": "1788729020181-0", "shadow_bc": "1787705526844-0"}
        self.peeks = []            # (since, streams) of every 1ms peek

    def read_lane_cursor(self):
        return dict(self.lane_cur)

    def wait(self, timeout_ms=0, limit=None, since=None, since_out=None, streams=None):
        if timeout_ms == 1:
            self.peeks.append((since, streams))
        if since is None and streams is None:
            return list(self.legacy_pending)      # the legacy family: stale 08-29 mail
        return []                                  # the lane family: at tail, nothing behind

    def cursor(self):
        return {"inbox": "1787969686471-0", "bc": "1787679775378-0"}

    def tail(self):
        return {}


def _api(bus):
    api = BifrostAPI.__new__(BifrostAPI)
    api.agent = "claude"
    api.bus = bus
    api._lane_since = None
    api._wake_since = None
    return api


def test_pending_peek_reads_the_lane_family_when_the_seat_has_a_lane_cursor(monkeypatch):
    """THE DEFECT at the seam: with a non-virgin lane cursor the arm-time peek must read the
    LANE streams from the LANE cursor -- not the legacy cursor nobody advances."""
    bus = _FamilyBus()
    api = _api(bus)
    monkeypatch.setattr(api, "_lane_tails", lambda: {"inbox": "$", "bc": "$"}, raising=False)

    got = api._wake_block_lane(timeout_ms=1)

    assert got == [], (
        f"stale legacy mail reported as pending ({_kinds(got)}) although the lane consumer "
        f"is at tail -- the peek read the legacy cursor family (frozen since 08-29)")
    assert bus.peeks, "the arm-time pending peek did not happen"
    since, streams = bus.peeks[0]
    assert streams == api._lane_streams(), "the pending peek must read the WORK-lane streams"
    assert since == {"inbox": bus.lane_cur["inbox"], "bc": bus.lane_cur["bc"]}, (
        "the pending peek must start from the lane cursor the consumer commits")


# ------------------------------------------ 1: committed-by-lane mail is NOT pending
def test_mail_the_lane_consumer_already_committed_is_not_pending(monkeypatch):
    """Live shape: legacy cursor virgin/stale, lane cursor at tail. A fresh arm must NOT
    fire on the legacy copy of mail the lane consumer already committed past."""
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.send("alice", "chat", "drained a week ago via the lane family")
    consumer = BifrostAPI("alice", namespace=ns)
    lane_key = consumer.bus.lane_cursor_key()
    shared_key = consumer.bus._cursor_key()
    lane_in = _lane_tail(c, f"{ns}:work:inbox:alice")
    assert lane_in != "0", "test precondition: the chat dual-wrote to the work lane"
    # the lane consumer committed past it (RB-26 commit-after-processing); legacy untouched
    assert consumer.bus.advance_to(inbox=lane_in, cursor_key=lane_key) == "OK"
    assert c.hgetall(shared_key) == {}, "test precondition: legacy cursor never advanced"
    lane_before, shared_before = c.hgetall(lane_key), c.hgetall(shared_key)

    fresh = BifrostAPI("alice", namespace=ns)                 # a NEW arm, new process shape
    got = fresh.wake_block(timeout_ms=50)

    assert got == [], (
        f"fresh arm fired on {_kinds(got)} -- the legacy copy of mail the lane consumer already "
        f"committed. 'pending' must mean behind the LANE cursor, not behind a legacy cursor "
        f"nobody advances (defer 224ac54766)")
    assert c.hgetall(lane_key) == lane_before, "detection wrote the lane cursor"
    assert c.hgetall(shared_key) == shared_before, "detection wrote the shared cursor"


# ------------------------------- 2: behind-the-lane-cursor mail IS pending (twin)
def test_mail_behind_the_lane_cursor_is_pending_whatever_legacy_says(monkeypatch):
    """The contract's other half: the lane consumer will redeliver everything behind its
    cursor, so the watcher must wake for it -- even when a legacy co-tenant swept the
    shared cursor past it (the same-token-twin shape the defer names)."""
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.broadcast("inform", "room noise the lane consumer already handled")
    legacy_mid = sender.send("alice", "chat", "still behind the lane cursor")
    consumer = BifrostAPI("alice", namespace=ns)
    lane_key = consumer.bus.lane_cursor_key()
    shared_key = consumer.bus._cursor_key()
    # lane family: ESTABLISHED (bc committed) but the directed chat is still behind
    lane_bc = _lane_tail(c, f"{ns}:work:broadcast")
    assert lane_bc != "0", "test precondition: the inform dual-wrote to the lane broadcast"
    assert consumer.bus.advance_to(bc=lane_bc, cursor_key=lane_key) == "OK"
    # legacy family: a co-tenant swept the shared cursor to the tails -- "all consumed"
    assert consumer.bus.advance_to(inbox=str(legacy_mid),
                                   bc=_lane_tail(c, f"{ns}:broadcast")) == "OK"
    lane_before, shared_before = c.hgetall(lane_key), c.hgetall(shared_key)

    fresh = BifrostAPI("alice", namespace=ns)
    got = fresh.wake_block(timeout_ms=50)

    assert got and "chat" in _kinds(got), (
        f"got {_kinds(got)}: mail still behind the LANE cursor must wake a fresh arm -- the "
        f"lane consumer will redeliver it, and the watcher's 'unread' must mean the consumer's")
    assert c.hgetall(lane_key) == lane_before, "detection wrote the lane cursor"
    assert c.hgetall(shared_key) == shared_before, "detection wrote the shared cursor"


# ---------------------------------------- 3: the seed warning names the family peeked
def test_seed_warning_names_the_lane_family_it_peeked(caplog, monkeypatch):
    """test_wake_pending_spin pins that seeding over non-empty pending is ANNOUNCED with a
    drain instruction. That instruction said BIFROST_CONSUME_LANE=legacy unconditionally --
    right for the legacy family, wrong once the peek reads the lane family: it would send
    the operator to drain the cursor that is NOT behind."""
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.broadcast("inform", "establishes the lane cursor")
    sender.send("alice", "chat", "behind the lane cursor")
    consumer = BifrostAPI("alice", namespace=ns)
    assert consumer.bus.advance_to(bc=_lane_tail(c, f"{ns}:work:broadcast"),
                                   cursor_key=consumer.bus.lane_cursor_key()) == "OK"

    fresh = BifrostAPI("alice", namespace=ns)
    with caplog.at_level(logging.WARNING, logger="bifrost"):
        got = fresh.wake_block(timeout_ms=50)

    assert got and "chat" in _kinds(got)
    warned = " ".join(r.getMessage() for r in caplog.records)
    assert "wake-worthy" in warned, "seeding over non-empty pending must stay announced"
    assert "BIFROST_CONSUME_LANE=work" in warned, (
        f"the drain instruction must name the family that is behind (the lane family); got: "
        f"{warned[-400:]!r}")
    assert "BIFROST_CONSUME_LANE=legacy" not in warned, (
        "the instruction still points at the legacy cursor, which is not the one behind")


# ---------------------------- 4: virgin lane hash -> legacy family stays the authority
def test_a_virgin_lane_hash_keeps_the_legacy_family_as_authority(monkeypatch):
    """Guard for the family-selection rule (green at HEAD, must stay green): a seat with NO
    lane cursor has never consumed in lane mode, so the legacy family still says what is
    unread. This is the MIGRANT case -- real legacy progress, unconsumed legacy backlog,
    virgin lane hash -- and the backlog must wake a fresh arm. (Seeding the lane hash at
    tails from the watcher would have silenced exactly this mail, which is why detection
    reads the family and never runs the flip ritual.)"""
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    first = sender.send("alice", "handoff", "consumed via legacy long ago")
    consumer = BifrostAPI("alice", namespace=ns)
    assert consumer.bus.advance_to(inbox=str(first)) == "OK"          # legacy progress
    assert c.hgetall(consumer.bus.lane_cursor_key()) == {}, "test precondition: virgin lane"
    sender.send("alice", "chat", "unconsumed legacy backlog")

    fresh = BifrostAPI("alice", namespace=ns)
    got = fresh.wake_block(timeout_ms=50)

    assert _kinds(got) == ["chat"], (
        f"got {_kinds(got)}: a migrant's unconsumed legacy backlog must wake a fresh arm "
        f"while its lane hash is virgin (legacy is still the family it consumes)")
    assert c.hgetall(consumer.bus.lane_cursor_key()) == {}, (
        "detection seeded the lane hash -- the watcher must stay detect-only")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# ---------------------------------------- 5: a note-heavy backlog must not hide the chat behind it
def test_a_note_heavy_backlog_does_not_hide_the_chat_behind_it(monkeypatch):
    """v5 refutation (2026-09-08): the first lane-aware peek decided 'pending' on the ten
    OLDEST ids and filtered PENDING_SKIP_KINDS afterwards, so twelve notes older than one
    directed chat read as 'nothing pending' -- the watcher seeded past the chat and slept.
    Live shape: dsh_agent's lane peek returned ten notes with 178 wake-worthy entries behind
    them. A wrong 'not pending' is a seat sleeping through mail; a false wake is cheap."""
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.broadcast("inform", "establishes the lane broadcast")
    sender.send("alice", "chat", "establishes the lane inbox")
    consumer = BifrostAPI("alice", namespace=ns)
    lane_key = consumer.bus.lane_cursor_key()
    shared_key = consumer.bus._cursor_key()
    streams = consumer._lane_streams()
    # lane family: ESTABLISHED at both tails -- everything so far is committed
    assert consumer.bus.advance_to(inbox=_lane_tail(c, streams["inbox"]),
                                   bc=_lane_tail(c, streams["bc"]), cursor_key=lane_key) == "OK"
    # then a note storm OLDER than the one directed chat, all behind the lane cursor
    for i in range(12):
        sender.broadcast("note", f"room noise {i}")
    sender.send("alice", "chat", "the mail behind the noise")
    lane_before, shared_before = c.hgetall(lane_key), c.hgetall(shared_key)

    fresh = BifrostAPI("alice", namespace=ns)
    got = fresh.wake_block(timeout_ms=50)

    assert got and "chat" in _kinds(got), (
        f"got {_kinds(got)}: twelve notes older than one directed chat must never read as "
        f"'nothing pending' -- the peek must filter skip-kinds BEFORE it decides, and page")
    assert c.hgetall(lane_key) == lane_before, "detection wrote the lane cursor"
    assert c.hgetall(shared_key) == shared_before, "detection wrote the shared cursor"
