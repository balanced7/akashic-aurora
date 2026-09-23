"""RED — an armed watcher whose session is gone wakes nobody, and reads as reachable.

FOUND BY THE FIX FINDING ITSELF WRONG, twenty minutes after it shipped (f591f2f5). Having
replaced presence with reachability on the Discord path, I verified live and got:

    presence LIVE : True
    any_armed     : armed
    REACHABLE     : True

All three were true statements and the conclusion was false. The armed seat belonged to session
`pin-ephemeral-0000` -- a REAL bifrost_wake process (pid 58216, cmdline confirmed) left running
by a drill. My actual session had no seat at all: its watcher had fired and exited,
correctly cleaning up after itself.

WHY IT MATTERS, precisely. The wake mechanism is PROCESS EXIT RE-INVOKING THE OWNING SESSION.
A watcher whose owning session is not a live conversation exits into nothing. It is armed, it is
real, it wakes no one -- and because `any_armed` aggregates across every session of an agent, it
made the whole agent read as reachable. One stray drill process can therefore mask an entirely
unreachable agent, which is the exact failure the predicate was written to end, one layer deeper.

This is the same class a third time in one night: a proxy standing in for the real question.
`watcher_state` asks "is the pid alive"; `any_armed` asks "is anything armed for this agent";
neither asks "is anything armed that can actually reach a living session".

  S1  armed for a session that is NOT live      -> NOT reachable   (the pin-ephemeral case)
  S2  armed for a session that IS live          -> reachable
  S3  several seats, only a dead session armed  -> NOT reachable
  S4  several seats, one live session armed     -> reachable       (ANY live match suffices)
  S5  no live sessions at all                   -> NOT reachable
  S6  live_sessions not supplied                -> prior behaviour, unchanged (strangler)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import wake_seat

# SYNTHETIC, never a real session id: a live session id in a tracked file is a
# privacy leak by the house's own standing rule, and this repo is public.
LIVE = "aaaaaaaa-0000-4444-8888-000000000001"
GONE = "pin-ephemeral-0000"


def _seat(tmp, session, pid=None):
    p = wake_seat.seat_path("claude", session, str(tmp))
    with open(p, "w") as f:
        f.write(str(pid if pid is not None else os.getpid()))
    return p


def _reach(tmp, live_sessions):
    return wake_seat.reachable("claude", presence_live=True,
                               live_sessions=live_sessions, tmp=str(tmp))


def test_s1_armed_for_a_dead_session_is_not_reachable(tmp_path):
    """THE PIN THIS FILE EXISTS FOR. A real watcher, a session that no longer exists."""
    _seat(tmp_path, GONE)
    assert _reach(tmp_path, {LIVE}) is False, \
        "S1: a watcher whose owning session is gone exits into nothing -- it must not make the " \
        "agent read as reachable"


def test_s2_armed_for_a_live_session_is_reachable(tmp_path):
    _seat(tmp_path, LIVE)
    assert _reach(tmp_path, {LIVE}) is True


def test_s3_only_dead_session_armed_among_several(tmp_path):
    _seat(tmp_path, GONE)
    _seat(tmp_path, "another-ghost-session")
    assert _reach(tmp_path, {LIVE}) is False


def test_s4_any_live_match_suffices(tmp_path):
    """The D2b rule survives: one genuinely live armed session is enough."""
    _seat(tmp_path, GONE)
    _seat(tmp_path, LIVE)
    assert _reach(tmp_path, {LIVE}) is True


def test_s5_no_live_sessions_at_all(tmp_path):
    _seat(tmp_path, GONE)
    assert _reach(tmp_path, set()) is False


def test_s6_omitting_live_sessions_keeps_the_prior_contract(tmp_path):
    """Strangler discipline: callers that do not pass live_sessions behave exactly as before,
    so f591f2f5's eleven pins keep their meaning."""
    _seat(tmp_path, GONE)
    assert wake_seat.reachable("claude", presence_live=True, tmp=str(tmp_path)) is True
    assert wake_seat.reachable("claude", presence_live=False, tmp=str(tmp_path)) is False


def test_a_dead_pid_for_a_live_session_is_still_not_reachable(tmp_path):
    """Both conditions are necessary: the session must be live AND the watcher alive."""
    _seat(tmp_path, LIVE, pid=999_999_998)
    assert _reach(tmp_path, {LIVE}) is False
