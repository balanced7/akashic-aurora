"""A session seat drains its steer queue at the turn boundary, and says so.

MEASURED TONIGHT, 2026-08-19. I pushed one steering fact at each seat and watched the queues:

    t=0s   {'claude': 1, 'deepseek': 0, 'kimi': 2}
    t=45s  {'claude': 1, 'deepseek': 0, 'kimi': 0}
    t=90s  {'claude': 1, 'deepseek': 0, 'kimi': 0}

Both runners popped theirs between tool rounds. Mine sat at 1 for the full ninety seconds,
because session seats have no round loop to drain it -- the exact defect codex_nudge_audit filed
on 2026-07-17 (`session_seat_no_steer_drain`) and nobody closed in the month since.

BOTH HALVES, because the negative half alone overstates it: `bifrost-nudge --mode steer` also
sends a bus copy, so the words are not destroyed. But "steer" sits in PENDING_SKIP_KINDS, so the
copy never counts as unread, never wakes the seat, and never announces itself. What is lost is the
one property that makes a steer a steer: FOLDING INTO WORK ALREADY IN PROGRESS.

So the fleet's steering was asymmetric -- the conductor could steer every seat and no seat could
steer the conductor. This closes it at the granularity a session seat can honestly offer: the TURN
boundary, not the tool round. The render says which one it is rather than implying parity, on the
T120 rule that a time-bound surface declares its bounds.

Run:  py -m pytest tests/test_session_seat_steer_drain.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from agent import bifrost_pull as BP  # noqa: E402


class _FakeNudge:
    """Stands in for the Redis-backed queue. The pins must never touch the LIVE steer queue --
    a test that drains a real seat's steering facts destroys another agent's mail."""

    def __init__(self, facts):
        self.facts = list(facts)
        self.drained = 0

    def steer_pending(self, agent):
        return len(self.facts)

    def steer_drain(self, agent):
        self.drained += 1
        out, self.facts = self.facts, []
        return out


def test_silent_when_nothing_is_queued():
    """No steer, no section. A surface that prints a header over nothing trains people to skip it."""
    assert BP.steer_facts_lines("claude", nudge=_FakeNudge([])) == []


def test_renders_every_fact_and_names_its_sender():
    fake = _FakeNudge(["[from deepseek] rooms board is mine, do not mint a ninth clipper",
                       "[from kimi] capture rows will carry provenance"])
    lines = BP.steer_facts_lines("claude", nudge=fake)
    body = "\n".join(lines)
    assert "deepseek" in body and "kimi" in body, body
    assert "ninth clipper" in body and "provenance" in body, body


def test_it_actually_drains():
    """The whole defect was a queue nobody popped."""
    fake = _FakeNudge(["[from deepseek] one fact"])
    BP.steer_facts_lines("claude", nudge=fake)
    assert fake.drained == 1
    assert fake.steer_pending("claude") == 0


def test_it_declares_the_granularity_it_can_honestly_offer():
    """T120: a time-bound surface states its bounds. A session seat folds at TURN boundaries, and
    pretending parity with a runner's between-rounds drain would be the comfortable lie."""
    lines = BP.steer_facts_lines("claude", nudge=_FakeNudge(["[from kimi] x"]))
    body = "\n".join(lines).lower()
    assert "turn" in body, body
    assert "round" in body, "it must name what it is NOT, or the caveat is decoration"


def test_peek_mode_does_not_consume():
    """--json and read-only callers must be able to look without eating another turn's mail."""
    fake = _FakeNudge(["[from deepseek] one fact"])
    lines = BP.steer_facts_lines("claude", nudge=fake, drain=False)
    assert lines, "peek still renders"
    assert fake.drained == 0 and fake.steer_pending("claude") == 1


def test_fail_open_never_wedges_the_sync():
    """steer_drain is fail-open by contract (nudge.py: 'never wedge the loop'). The renderer
    inherits that: a broken backend costs the facts, not the seat's turn."""
    class _Broken:
        def steer_pending(self, agent):
            raise RuntimeError("redis is having a night")

        def steer_drain(self, agent):
            raise RuntimeError("redis is having a night")

    assert BP.steer_facts_lines("claude", nudge=_Broken()) == []
