"""
T014 regression — bifrost_runner_deepseek: backlog cursor-skip + reply routing + echo-loop guard.

Tests the THREE fixes applied in T014 without needing an API key:
  (a) Bus _drain: with more messages than limit, cursor advances only to the last RETURNED
      message, not the last READ message (the cursor-skip fix).
  (b) Directed reply lands in the requester's inbox (bus.send to a specific agent → that agent's
      inbox has it; a third agent's inbox does not).
  (c) 'reply' is NOT in ANSWERABLE → no runner↔runner echo loop possible (unit test on the
      constant + should_answer).

Run: py -m pytest tests/test_bifrost_runner_deepseek.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from bifrost_runner_deepseek import ANSWERABLE, should_answer


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_t014_{uuid.uuid4().hex[:8]}"


def _cleanup(client, ns):
    keys = client.keys(f"{ns}:*")
    if keys:
        client.delete(*keys)


# =========================================================================== (c) echo-loop guard
class TestReplyEchoGuard:
    """'reply' must NEVER be in ANSWERABLE — the anti-loop contract."""

    def test_reply_not_answerable(self):
        assert "reply" not in ANSWERABLE, \
            "'reply' kind must NOT be answerable — no runner↔runner echo loop"

    def test_should_answer_rejects_reply(self):
        assert should_answer("reply", "claude", "deepseek") is False, \
            "a reply from another agent must NOT trigger a reply (loop guard)"

    def test_own_echo_rejected(self):
        assert should_answer("chat", "deepseek", "deepseek") is False, \
            "own message must not trigger a reply"

    def test_answerable_kinds_accepted(self):
        for k in ("chat", "request", "question", "handoff", "nudge", "inform"):
            assert should_answer(k, "claude", "deepseek") is True, \
                f"kind '{k}' from another agent must be answerable"

    def test_steer_not_answerable(self):
        assert should_answer("steer", "claude", "deepseek") is False, \
            "'steer' is folded into current task, never triggers a standalone reply"
        assert "steer" not in ANSWERABLE


# =========================================================================== (a) cursor-skip fix
class TestDrainCursorSkipFix:
    """Bus._drain: cursor advances only to the last RETURNED message, not the last READ."""

    def test_cursor_advances_to_returned_only(self):
        """With 5 messages and limit=3, cursor advances to the 3rd, not the 5th.
        The remaining 2 should be readable on a subsequent call."""
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            alice = Bus("alice", c, namespace=ns)
            bob = Bus("bob", c, namespace=ns)

            # Send 5 messages
            for i in range(5):
                alice.send("bob", "chat", f"m{i}")

            # Read with limit=3, advance=True (the runner's pattern)
            first = bob.inbox(limit=3, advance=True)
            assert len(first) == 3, f"first drain returned {len(first)}, expected 3"
            assert [m.content for m in first] == ["m0", "m1", "m2"]

            # The remaining 2 MUST still be readable — this is the fix
            second = bob.inbox(limit=10, advance=True)
            assert len(second) == 2, \
                f"second drain returned {len(second)}, expected 2 (the cursor-skip regression)"
            assert [m.content for m in second] == ["m3", "m4"]

            # Third drain should be empty
            third = bob.inbox(limit=10, advance=True)
            assert third == [], f"third drain should be empty, got {[m.content for m in third]}"
        finally:
            _cleanup(c, ns)

    def test_cursor_skip_regression_mixed_streams(self):
        """With direct + broadcast messages and limit<total, no messages are silently lost."""
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            alice = Bus("alice", c, namespace=ns)
            bob = Bus("bob", c, namespace=ns)
            carol = Bus("carol", c, namespace=ns)

            # Mix: direct to bob + broadcast (which bob sees too)
            alice.send("bob", "chat", "d1")
            alice.broadcast("note", "b1")
            alice.send("bob", "chat", "d2")
            alice.broadcast("note", "b2")
            alice.send("bob", "chat", "d3")

            # Bob should see 5 (3 direct + 2 broadcast, minus own-broadcast filter which
            # doesn't apply since alice sent the broadcasts)
            all5 = bob.inbox(limit=100, advance=False)
            assert len(all5) == 5, f"expected 5 pending (3 direct + 2 broadcast), got {len(all5)}"

            # Now read with limit=2
            first = bob.inbox(limit=2, advance=True)
            assert len(first) == 2

            # Remaining 3 must be readable
            rest = bob.inbox(limit=10, advance=True)
            assert len(rest) == 3, \
                f"expected 3 remaining after limit=2 drain, got {len(rest)} (cursor-skip regression)"

            empty = bob.inbox(limit=10, advance=True)
            assert empty == []
        finally:
            _cleanup(c, ns)

    def test_advance_false_does_not_move_cursor(self):
        """Peek (advance=False) must never consume — the cursor stays put."""
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            alice = Bus("alice", c, namespace=ns)
            bob = Bus("bob", c, namespace=ns)

            alice.send("bob", "chat", "x")
            alice.send("bob", "chat", "y")

            # Peek twice
            peek1 = bob.inbox(limit=10, advance=False)
            assert len(peek1) == 2
            peek2 = bob.inbox(limit=10, advance=False)
            assert len(peek2) == 2, \
                "peek (advance=False) must not consume — cursor should not move"

            # Now consume
            got = bob.inbox(limit=10, advance=True)
            assert len(got) == 2
            assert bob.inbox(limit=10, advance=True) == []
        finally:
            _cleanup(c, ns)

    def test_limit_one_still_drains_all_eventually(self):
        """limit=1 across many wakes must drain all messages one-by-one."""
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            alice = Bus("alice", c, namespace=ns)
            bob = Bus("bob", c, namespace=ns)

            # Pre-queue 4
            for i in range(4):
                alice.send("bob", "chat", f"p{i}")

            # Drain one at a time (simulates repeated --once runner wakes)
            collected = []
            for _ in range(4):
                batch = bob.inbox(limit=1, advance=True)
                if batch:
                    collected.append(batch[0].content)
                else:
                    break

            assert collected == ["p0", "p1", "p2", "p3"], \
                f"limit=1 sequential drain lost messages: got {collected}"
            assert bob.inbox(limit=10, advance=True) == [], \
                "nothing left after draining all"
        finally:
            _cleanup(c, ns)


# =========================================================================== (b) directed reply routing
class TestDirectedReplyRouting:
    """A directed send lands in the recipient's inbox, not anybody else's."""

    def test_directed_reply_in_recipient_inbox(self):
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            deepseek = Bus("deepseek", c, namespace=ns)
            claude = Bus("claude", c, namespace=ns)
            gemini = Bus("gemini", c, namespace=ns)

            # DeepSeek sends a directed reply to Claude
            deepseek.send("claude", "reply", "here is the answer")

            # Claude should see it
            claude_msgs = claude.inbox()
            assert len(claude_msgs) == 1
            assert claude_msgs[0].frm == "deepseek"
            assert claude_msgs[0].to == "claude"
            assert claude_msgs[0].kind == "reply"
            assert claude_msgs[0].content == "here is the answer"

            # Gemini must NOT see it
            gemini_msgs = gemini.inbox()
            assert gemini_msgs == [], \
                "a directed reply must NOT leak to a third agent"

            # DeepSeek must NOT see its own sent message
            deepseek_msgs = deepseek.inbox()
            assert deepseek_msgs == [], \
                "a sender must not receive its own sent message"
        finally:
            _cleanup(c, ns)

    def test_reply_visible_via_pending_peek(self):
        """The recipient can peek a reply without consuming it (bifrost-sync works)."""
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            deepseek = Bus("deepseek", c, namespace=ns)
            claude = Bus("claude", c, namespace=ns)

            deepseek.send("claude", "reply", "the answer")

            # Pending shows it
            assert claude.pending() == 1, "directed reply must count as pending"

            # Peek shows it (advance=False)
            peek = claude.inbox(limit=10, advance=False)
            assert len(peek) == 1
            assert peek[0].kind == "reply"

            # Still pending after peek
            assert claude.pending() == 1

            # Consume
            assert len(claude.inbox()) == 1
            assert claude.pending() == 0
        finally:
            _cleanup(c, ns)

    def test_broadcast_reply_visible_to_all(self):
        """A broadcast reply reaches every agent (except sender)."""
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            deepseek = Bus("deepseek", c, namespace=ns)
            claude = Bus("claude", c, namespace=ns)
            gemini = Bus("gemini", c, namespace=ns)

            deepseek.broadcast("reply", "public answer")

            # Everyone except sender sees it. (claude-review fix: inbox() CONSUMES by
            # default -- the original double-call here would IndexError on the second read.)
            cl = claude.inbox()
            assert len(cl) == 1 and cl[0].kind == "reply"
            gm = gemini.inbox()
            assert len(gm) == 1 and gm[0].kind == "reply"
            assert deepseek.inbox() == [], \
                "sender must not receive its own broadcast"
        finally:
            _cleanup(c, ns)

    def test_multiple_directed_replies_all_land(self):
        """Multiple directed replies from different senders all arrive."""
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            deepseek = Bus("deepseek", c, namespace=ns)
            gemini = Bus("gemini", c, namespace=ns)
            claude = Bus("claude", c, namespace=ns)

            deepseek.send("claude", "reply", "ds answer")
            gemini.send("claude", "reply", "gm answer")
            deepseek.send("claude", "chat", "followup question")

            msgs = claude.inbox()
            assert len(msgs) == 3
            kinds = [m.kind for m in msgs]
            assert kinds.count("reply") == 2
            assert kinds.count("chat") == 1
            contents = {m.content for m in msgs}
            assert contents == {"ds answer", "gm answer", "followup question"}
        finally:
            _cleanup(c, ns)


# ======================================================== (claude review) filtered != truncated
class TestFilteredAdvance:
    """Adversarial-review refinement: FILTERED entries (an agent's own broadcasts) must still
    advance the cursor when nothing was truncated -- filtered != truncated. Without this, a
    chatty broadcaster's every future drain re-scans its own backlog forever."""

    def test_own_broadcasts_do_not_stall_the_cursor(self):
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            bob = Bus("bob", c, namespace=ns)
            alice = Bus("alice", c, namespace=ns)
            bob.broadcast("note", "own1")
            bob.broadcast("note", "own2")
            bob.broadcast("note", "own3")
            alice.send("bob", "chat", "for bob")
            got = bob.inbox(limit=10, advance=True)   # 4 read, 1 deliverable, NO truncation
            assert [m.content for m in got] == ["for bob"]
            cur = c.hgetall(f"{ns}:cursor:bob")
            assert cur.get("bc", "0") != "0", \
                "own-broadcast entries must advance the bc cursor when nothing was truncated"
            assert bob.inbox(limit=10, advance=True) == []
        finally:
            _cleanup(c, ns)

    def test_truncation_still_protects_the_tail_around_filtered_entries(self):
        """Truncation + filtered interleave: the unreturned tail survives; the filtered
        middle clears on the following (untruncated) drain."""
        c, ns = _client(), _ns()
        try:
            from core.comm.bus import Bus
            bob = Bus("bob", c, namespace=ns)
            alice = Bus("alice", c, namespace=ns)
            alice.send("bob", "chat", "d1")
            bob.broadcast("note", "own-mid")
            alice.send("bob", "chat", "d2")
            first = bob.inbox(limit=1, advance=True)          # truncation branch
            assert [m.content for m in first] == ["d1"]
            rest = bob.inbox(limit=10, advance=True)          # untruncated branch
            assert [m.content for m in rest] == ["d2"], f"truncation tail lost: {rest}"
            assert bob.inbox(limit=10, advance=True) == []
        finally:
            _cleanup(c, ns)


if __name__ == "__main__":
    # Smoke: run the unit tests (not the Redis-backed ones)
    TestReplyEchoGuard().test_reply_not_answerable()
    TestReplyEchoGuard().test_should_answer_rejects_reply()
    TestReplyEchoGuard().test_own_echo_rejected()
    TestReplyEchoGuard().test_answerable_kinds_accepted()
    TestReplyEchoGuard().test_steer_not_answerable()
    print("ROUTING TESTS PASSED (redis-backed tests run under pytest)")
