"""RED — a LIVE seat is not a REACHABLE seat, and Discord has been reporting the wrong one.

THE INCIDENT (2026-09-17 .. 2026-09-23). Four directed Discord messages from the operator sat
unread, two of them for five days. Nothing was broken in the transport: they were delivered,
durably, to a seat that was LIVE and beating the whole time.

The Discord inbound path asks one question before deciding whether to tell him nobody is home:

    scripts/bifrost_runner_discord.py:_is_seat_live()
        -> roster worklive state == "LIVE"

and `_auto_wake` reads a True as "the lane plus its armed wake listener ARE the wake" — which is
correct ONLY if a listener is in fact armed. On the night in question the seat was live and NO
wake listener was armed, so the honest answer was "nobody will read this", the predicate said
LIVE, `_auto_wake` stayed silent, no 📭 was posted, and the operator got silence that looked
exactly like being ignored.

A LIVE SEAT WITH NO ARMED LISTENER IS A LIT ROOM WITH NOBODY IN IT. Presence and reachability
are two questions under one name, which is the defect class this house has now named five times.

Measured while writing these pins, on the live system: presence LIVE=True, wake seats found=0.
The old predicate said reachable; the true answer was not.

A SECOND FINDING, in the docstring rather than the code. `_is_seat_live` fails OPEN (any probe
error reads as LIVE) and justifies it: "the cost of a false 'not live' repeated on every hiccup
is a duplicate paid seat per message." That cost was real when a cold seat auto-SPAWNED a
headless claude. The 2026-09-04 ruling removed spawning entirely -- a cold seat now only posts a
notice. So the expensive half of that trade no longer exists, while the cheap half became five
days of lost operator mail. The fail-open direction was chosen under a cost model since repealed;
these pins keep fail-open ONLY where the probe genuinely cannot tell.

  D1  LIVE + no wake seat at all      -> NOT reachable   (the incident)
  D2  LIVE + an armed wake seat       -> reachable
  D3  LIVE + a dead-seat pid file     -> NOT reachable   (the 08-12 stale-seat shape)
  D4  LIVE + only 'unknown'           -> reachable       (claim NEITHER direction, A4)
  D5  not LIVE                        -> NOT reachable   (unchanged)
  D6  probe raises                    -> reachable       (fail open, unchanged contract)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import wake_seat


def _seat(tmp, agent, session, pid):
    p = wake_seat.seat_path(agent, session, str(tmp))
    with open(p, "w") as f:
        f.write(str(pid))
    return p


# --------------------------------------------------------------- the aggregate predicate
def test_d1_no_seat_file_at_all_is_unarmed(tmp_path):
    """The incident's exact shape: nothing armed anywhere for this agent."""
    assert wake_seat.any_armed("claude", tmp=str(tmp_path)) == "unarmed"


def test_d2_one_armed_session_is_armed(tmp_path):
    _seat(tmp_path, "claude", "s1", os.getpid())      # our own pid is certainly alive
    assert wake_seat.any_armed("claude", tmp=str(tmp_path)) == "armed"


def test_d2b_one_armed_among_several_is_enough(tmp_path):
    _seat(tmp_path, "claude", "dead", 999_999_998)
    _seat(tmp_path, "claude", "live", os.getpid())
    assert wake_seat.any_armed("claude", tmp=str(tmp_path)) == "armed", \
        "D2b: ANY armed session makes the agent reachable -- a stale sibling must not mask it"


def test_d3_only_dead_seats_is_dead_seat(tmp_path):
    """A seat file whose pid is gone. The 2026-08-12 failure: the file looks like an arm."""
    _seat(tmp_path, "claude", "s1", 999_999_998)
    assert wake_seat.any_armed("claude", tmp=str(tmp_path)) == "dead-seat"


def test_d4_unreadable_pid_is_unknown_never_a_verdict(tmp_path):
    """watcher_state's own law: claim NEITHER direction when the probe cannot tell."""
    p = wake_seat.seat_path("claude", "s1", str(tmp_path))
    with open(p, "w") as f:
        f.write("not-a-pid")
    assert wake_seat.any_armed("claude", tmp=str(tmp_path)) == "unknown"


def test_the_four_states_are_total(tmp_path):
    """An unlisted case resolves; it never raises and never silently reads as armed."""
    assert wake_seat.any_armed("nobody-here", tmp=str(tmp_path)) in (
        "armed", "unarmed", "dead-seat", "unknown")


# --------------------------------------------------------------- the composed verdict
def test_d5_reachability_requires_presence_too(tmp_path):
    """Armed but not present is not reachable either -- both halves are necessary."""
    _seat(tmp_path, "claude", "s1", os.getpid())
    assert wake_seat.reachable("claude", presence_live=False, tmp=str(tmp_path)) is False


def test_d1_composed_live_but_unarmed_is_not_reachable(tmp_path):
    """THE PIN THIS FILE EXISTS FOR. Live, beating, and nobody listening."""
    assert wake_seat.reachable("claude", presence_live=True, tmp=str(tmp_path)) is False, \
        "D1: a LIVE seat with no armed listener must NOT report as reachable -- this is the " \
        "exact state in which four operator messages were lost"


def test_d2_composed_live_and_armed_is_reachable(tmp_path):
    _seat(tmp_path, "claude", "s1", os.getpid())
    assert wake_seat.reachable("claude", presence_live=True, tmp=str(tmp_path)) is True


def test_d4_composed_unknown_stays_reachable(tmp_path):
    """Fail open ONLY here: the probe genuinely cannot tell, so assert nothing."""
    p = wake_seat.seat_path("claude", "s1", str(tmp_path))
    with open(p, "w") as f:
        f.write("not-a-pid")
    assert wake_seat.reachable("claude", presence_live=True, tmp=str(tmp_path)) is True


def test_d6_a_raising_probe_fails_open(tmp_path):
    """Contract preserved from _is_seat_live: a crashed probe never cries unreachable."""
    def boom(_pid):
        raise RuntimeError("probe exploded")
    _seat(tmp_path, "claude", "s1", os.getpid())
    assert wake_seat.reachable("claude", presence_live=True, tmp=str(tmp_path),
                               pid_probe=boom) is True
