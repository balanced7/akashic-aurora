"""Sync-peek freshness pin -- RED first (M3).

THE DEFECT (kimi's Q4 winner, adopted 3/3 in the build-queue synthesis; lived at this
session's boot): peek_inbox() renders the OLDEST `limit` unread messages, so with a stale
backlog ahead of the cursor the peek shows the SAME old items on every call and NEWLY
ARRIVED mail is invisible. At session start this masked three real replies behind ten
stale notices; the seat had to bypass the cursor with raw xrange to find them. The organ
whose one job is "what is waiting for you" hid exactly the mail that mattered.

THE PIN: with a backlog larger than the render limit, a message that arrives LAST must
still be visible in the peek. Oldest-context may be shown too -- but freshness must never
be sacrificed to staleness. The header must also confess when it is windowing
(pending_at_least > shown), so a truncated view can never read as the whole.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus  # noqa: E402
from agent.bifrost_pull import peek_inbox  # noqa: E402

AGENT = f"peekpin_{uuid.uuid4().hex[:6]}"


def test_newest_mail_visible_through_stale_backlog():
    sender = Bus("deepseek")
    if not sender.online:
        print("SKIPPED (Redis not running)")
        return
    for i in range(30):
        sender.send(AGENT, "note", f"stale-backlog-{i}")
    sender.send(AGENT, "reply", "THE-FRESH-REPLY-THAT-MATTERS")

    msgs = peek_inbox(AGENT, limit=10)
    bodies = " | ".join(str(m.get("content", "")) for m in msgs)
    assert "THE-FRESH-REPLY-THAT-MATTERS" in bodies, (
        f"FRESHNESS MASKED: 31 unread, peek limit 10 rendered only the oldest -- the newest "
        f"message (a REPLY) is invisible. This is the exact failure that hid three real "
        f"replies behind ten stale notices at boot. Peek rendered: {bodies[:400]}")


def test_windowed_peek_confesses_the_hidden_middle():
    sender = Bus("deepseek")
    if not sender.online:
        print("SKIPPED (Redis not running)")
        return
    agent = AGENT + "w"
    for i in range(25):
        sender.send(agent, "note", f"bulk-{i}")

    msgs = peek_inbox(agent, limit=8)
    # The return must carry an honest at-least count exceeding what is shown, so no renderer
    # can present a window as the whole inbox (the confident-zero shape in a mail view).
    total = max((int(m.get("pending_at_least", 0)) for m in msgs), default=0)
    assert total > len([m for m in msgs if not m.get("gap")]), (
        f"WINDOW WITHOUT CONFESSION: 25 unread, 8 shown, and nothing in the peek result "
        f"carries pending_at_least > shown. A truncated view that does not say so reads as "
        f"the whole inbox. Result keys: {[sorted(m.keys()) for m in msgs[:2]]}")


def test_true_tail_visible_beyond_the_overread_cap():
    """Sol's blocker (independent review of b05e08f/c47be4a, REPRODUCED at 80 msgs):
    the over-read XREADs oldest-first from the cursor, so with backlog > cap (50) the
    window's "newest" is the newest OF THE OLDEST 50 -- the TRUE tail (msg-079) is
    invisible, exactly in the storm condition freshness exists for. The 31-message pin
    could not expose it (31 < 50). This pin uses 80 and asserts GENUINE tail visibility.
    Fix contract: true-tail logic (reverse-range merge), not a larger magic cap."""
    sender = Bus("deepseek")
    if not sender.online:
        print("SKIPPED (Redis not running)")
        return
    agent = AGENT + "t"
    for i in range(80):
        sender.send(agent, "note", f"deep-backlog-{i:03d}")

    msgs = peek_inbox(agent, limit=10)
    bodies = " | ".join(str(m.get("content", "")) for m in msgs)
    assert "deep-backlog-079" in bodies, (
        f"TRUE TAIL INVISIBLE: 80 unread, over-read cap 50 -- the window's 'newest' is the "
        f"newest of the OLDEST 50, and the genuinely newest message is hidden. Sol's "
        f"reproduction, pinned. Rendered: ...{bodies[-300:]}")


if __name__ == "__main__":
    test_newest_mail_visible_through_stale_backlog()
    test_windowed_peek_confesses_the_hidden_middle()
    test_true_tail_visible_beyond_the_overread_cap()
    print("PASS")
