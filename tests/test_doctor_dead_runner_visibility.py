"""
Regression pin for the 2026-07-12 gap: a dead-runner agent with a durable inbox backlog VANISHED
from the fleet doctor. worklive/runner-lock/presence are all TTL'd, so once deepseek's runner died
it decayed out of known_agents() within a minute -- and the (working) stalled_consumer check never
got to examine it. 7 unread asks sat unwatched while `doctor` reported "fleet healthy".

Fix: known_agents() also enumerates agents whose DURABLE inbox holds RECENT unconsumed mail, so a
stuck/absent consumer stays visible; recency-gated so long-retired agents' stale inboxes don't
resurrect as findings.
"""
import time

import pytest

from core.comm import doctor


def _client():
    return doctor._client()


pytestmark = pytest.mark.skipif(_client() is None, reason="bus/Redis offline")


def test_recent_inbox_agent_is_visible_stale_is_not():
    """The core fix: an inbox-only agent (no presence, no runner-lock) with RECENT mail is surfaced;
    one whose newest mail is older than the recency window is NOT."""
    c = _client()
    recent, stale = "zdoctest-recent", "zdoctest-stale"
    rkey, skey = f"bifrost:inbox:{recent}", f"bifrost:inbox:{stale}"
    try:
        c.delete(rkey, skey)
        c.xadd(rkey, {"kind": "request", "frm": "tester", "content": "fresh ask"})  # now
        old_ms = int((time.time() - doctor.RECENT_INBOX_S - 3600) * 1000)           # past the window
        c.xadd(skey, {"kind": "request", "frm": "tester", "content": "old ask"}, id=f"{old_ms}-0")

        ka = doctor.known_agents()
        assert recent in ka, "a dead-runner agent with RECENT unread mail must stay visible to the doctor"
        assert stale not in ka, "a long-retired agent's stale inbox must NOT resurrect as a finding"
    finally:
        c.delete(rkey, skey)


def test_visible_stalled_agent_pages():
    """End-to-end: an inbox-only agent with recent backlog is not just visible but graded a finding
    (dashboard before hysteresis, page after) -- proving the enumeration fix reconnects to the
    existing stalled_consumer detector."""
    c = _client()
    agent = "zdoctest-stalled"
    key = f"bifrost:inbox:{agent}"
    scur = f"bifrost:stalled_since:{agent}"
    try:
        c.delete(key, scur)
        c.xadd(key, {"kind": "request", "frm": "tester", "content": "please answer"})
        findings = doctor.examine(agent)
        states = {f["state"] for f in findings}
        assert "stalled_consumer" in states, f"expected a stalled_consumer finding, got {findings}"
    finally:
        c.delete(key, scur)
