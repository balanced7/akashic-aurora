"""
T380 -- Discord comms-stage reaction ladder: pins for the tracker (the pure half).

Bar (pre-registered BEFORE the implementation, M3; Heimdall's fence counter
1787417935818-0 folded -- one authority per fact, heuristics labeled in the render):

  P1  the seen-join is REAL across both producers: a message sent through the Bus,
      opened via the harness path (mailbox.open_for_message on the consumed shape),
      is found by the tracker's track-time identity -- same key form, same sha.
  P2  THINKING fires exactly once after the seen receipt exists (idempotent poll).
  P3  ANSWERED (strict) fires on a reply whose meta.answers == tracked mid; it
      settles the entry (no later thinking/replied ops for that mid).
  P4  REPLIED (heuristic, DISTINCT op from answered -- rendered as a different
      emoji, never the strict checkmark) fires on a directed non-trace message
      from an addressed seat, newer than the tracked mid, without meta.answers,
      inside REPLIED_WINDOW_S. Outside the window: no op (the lie is bounded).
  P5  DEAD fires when an expectation_dead record names the tracked mid in refs
      (events plane injected -- the reader is DI, per get_event_log(ledger=...)).

Redis-backed in a throwaway namespace, skip if down (pattern: test_bifrost_bus.py).
The discord half (reaction apply, staggering, evict-on-deleted) is runner wiring
under garnish-never-wounds; G1 is a live drill with a dated receipt.
Run: py -m pytest tests/test_t380_reaction_ladder.py -q
"""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus
from core.comm import mailbox
from core.comm.discord_ladder import LadderTracker, REPLIED_WINDOW_S


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"t380_test_{uuid.uuid4().hex[:8]}"


def _cleanup(client, ns):
    keys = client.keys(f"{ns}:*")
    if keys:
        client.delete(*keys)


def _operator_send(client, ns, text="hello from the car"):
    """One operator message relayed onto the bus, discord-shaped meta, as the
    gateway's inbound path sends it (frm=daniil, directed to the seat lane)."""
    b = Bus("daniil", client=client, namespace=ns, promote=False)
    mid = b.send("claude", "chat", text,
                 meta={"source": "discord", "operator": True, "speaker": "daniil"})
    assert mid, "bus refused the send; test cannot proceed"
    return b, str(mid)


def _tracker(client, ns, events_reader=None):
    return LadderTracker(client=client, ns=ns, operator="daniil",
                         events_reader=events_reader or (lambda: []))


def _track(t, b, mid, text="hello from the car"):
    t.track(mid, to_agents=["claude"], channel_id="chan1", discord_msg_id="dmsg1")
    return t


def _consumed_shape(client, ns, mid):
    """The message as a consumer sees it: the raw stream fields of the sent record."""
    b = Bus("claude", client=client, namespace=ns, promote=False)
    entries = client.xrange(b._inbox_key("claude"), min=mid, max=mid)
    assert entries, "sent message not found on its own inbox stream"
    _, fields = entries[0]
    return dict(fields)


# ------------------------------------------------------------------ P1 + P2: thinking
def test_p1_p2_thinking_fires_once_on_seen_receipt():
    c = _client()
    ns = _ns()
    try:
        b, mid = _operator_send(c, ns)
        t = _tracker(c, ns)
        _track(t, b, mid)

        assert t.poll() == [], "no seen receipt yet -- thinking must NOT fire"

        # the HARNESS producer: exactly what agent_cli's consume does (T133/M6)
        opened = mailbox.open_for_message(
            "claude", _consumed_shape(c, ns, mid), incarnation="testinc",
            ns=ns, client=c)
        assert opened.get("ok"), f"open_for_message failed: {opened}"

        ops = t.poll()
        assert [o["op"] for o in ops] == ["thinking"], f"expected one thinking op, got {ops}"
        assert ops[0]["discord_msg_id"] == "dmsg1"
        assert t.poll() == [], "thinking must be idempotent across polls"
    finally:
        _cleanup(c, ns)


# ------------------------------------------------------------------ P3: strict answer
def test_p3_strict_answer_settles_and_swallows():
    c = _client()
    ns = _ns()
    try:
        b, mid = _operator_send(c, ns)
        t = _tracker(c, ns)
        _track(t, b, mid)

        seat = Bus("claude", client=c, namespace=ns, promote=False)
        rid = seat.send("daniil", "reply", "here is your answer",
                        meta={"answers": mid})
        assert rid

        ops = t.poll()
        assert [o["op"] for o in ops] == ["answered"], f"expected answered, got {ops}"

        # settled: a later seen receipt must not resurrect thinking
        opened = mailbox.open_for_message(
            "claude", _consumed_shape(c, ns, mid), incarnation="testinc",
            ns=ns, client=c)
        assert opened.get("ok")
        assert t.poll() == [], "settled entry must emit nothing further"
    finally:
        _cleanup(c, ns)


# ------------------------------------------------------------------ P4: heuristic reply
def test_p4_unlinked_reply_is_distinct_op_and_window_capped():
    c = _client()
    ns = _ns()
    try:
        b, mid = _operator_send(c, ns)
        t = _tracker(c, ns)
        _track(t, b, mid)

        seat = Bus("claude", client=c, namespace=ns, promote=False)
        rid = seat.send("daniil", "chat", "writing back, no link")
        assert rid

        ops = t.poll()
        assert [o["op"] for o in ops] == ["replied"], (
            f"unlinked reply must be its own labeled op, never the strict checkmark: {ops}")

        # window cap: a stale entry must NOT be settled by fresh chatter
        b2, mid2 = _operator_send(c, ns, text="older question")
        t2 = _tracker(c, ns)
        t2.track(mid2, to_agents=["claude"], channel_id="chan1", discord_msg_id="dmsg2")
        t2._entries[mid2].tracked_ts = time.time() - (REPLIED_WINDOW_S + 60)
        rid2 = seat.send("daniil", "chat", "much later, unrelated")
        assert rid2
        assert t2.poll() == [], "outside REPLIED_WINDOW_S the heuristic must stay silent"
    finally:
        _cleanup(c, ns)


# ------------------------------------------------------------------ P5: expectation dead
def test_p5_expectation_dead_marks_dead():
    c = _client()
    ns = _ns()
    try:
        b, mid = _operator_send(c, ns)
        dead_records = []
        t = _tracker(c, ns, events_reader=lambda: list(dead_records))
        _track(t, b, mid)

        assert t.poll() == []
        dead_records.append({"kind": "expectation_dead", "refs": [mid]})
        ops = t.poll()
        assert [o["op"] for o in ops] == ["dead"], f"expected dead, got {ops}"
        assert t.poll() == [], "dead is terminal and idempotent"
    finally:
        _cleanup(c, ns)
