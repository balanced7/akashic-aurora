"""RED — the reviver asks whether a daemon PROCESS exists, not whether it is doing its job.

THE FIFTH RUNG. On 2026-09-23 four directed operator messages went unread, two for five days,
and chasing it to the bottom found the same defect at five separate layers of one path, each
answering a cheaper question than the one that mattered:

    _is_seat_live      presence          not  listening
    watcher_state      pid alive         not  watcher alive
    any_armed          armed somewhere   not  armed for a LIVING session
    stop hook          daemon exists     -> leaves a .rearm trigger and trusts it
    revive._live       PROCESS exists    not  daemon CONSUMING those triggers   <- this one

The first four are fixed (f591f2f5, 6d4cce6e). This is the last, and it is the one that would
have caught the whole cascade, because the reviver is the thing whose entire job is noticing.

THE MECHANISM IT MISSES. The stop hook, seeing a live daemon, writes a `.rearm` trigger and
passes -- it is the daemon's job to consume it (consume_rearms, only under --manage-listener)
and re-arm the listener. So a daemon that is ALIVE BUT NOT CONSUMING produces exactly the
observed failure: triggers pile up, nothing re-arms, the seat goes unreachable, and every
surface reports healthy. `_live()` is a command-line string match; a wedged daemon matches it
perfectly.

THREE STATES, NOT TWO, and the remedies differ -- which is why they must be distinguishable:

    working   process alive and triggers being consumed   -> nothing
    WEDGED    process alive, triggers going stale         -> RESTART (kill, then spawn)
    down      no process                                  -> SPAWN

Collapsing wedged into working is the silence this fixes. Collapsing wedged into down is worse:
`decide()` would spawn a SECOND daemon beside the wedged one, which is how duplicates breed.

  D1  a fresh trigger is not a wedge -- the daemon gets its tick
  D2  a trigger older than the tolerance IS a wedge
  D3  no triggers at all is never a wedge (nothing to consume)
  D4  the wedge verdict is distinct from BOTH healthy and down
  D5  an unreadable probe reports unknown, never 'fine' -- the A4 law
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import daemon_state


def _trigger(tmp, agent, sid, age_s=0.0):
    p = daemon_state.rearm_path(agent, sid, str(tmp))
    with open(p, "w", encoding="utf-8") as f:
        f.write(str(time.time()))
    if age_s:
        old = time.time() - age_s
        os.utime(p, (old, old))
    return p


def test_d1_a_fresh_trigger_is_not_a_wedge(tmp_path):
    _trigger(tmp_path, "claude", "s1", age_s=5)
    state, detail = daemon_state.rearm_backlog_state("claude", tmp=str(tmp_path),
                                                     tolerance_s=180)
    assert state == "working", detail


def test_d2_a_stale_trigger_is_a_wedge(tmp_path):
    _trigger(tmp_path, "claude", "s1", age_s=900)
    state, detail = daemon_state.rearm_backlog_state("claude", tmp=str(tmp_path),
                                                     tolerance_s=180)
    assert state == "wedged", detail
    assert "s1" in detail or "1" in detail, "D2: the detail must name what is going unconsumed"


def test_d3_no_triggers_is_never_a_wedge(tmp_path):
    state, _ = daemon_state.rearm_backlog_state("claude", tmp=str(tmp_path), tolerance_s=180)
    assert state == "working", "D3: nothing to consume is not a failure to consume"


def test_d4_wedged_is_its_own_state(tmp_path):
    """The remedies differ -- restart vs spawn -- so the states must differ. Collapsing
    wedged into down makes decide() spawn a duplicate beside the wedged one."""
    _trigger(tmp_path, "claude", "s1", age_s=900)
    state, _ = daemon_state.rearm_backlog_state("claude", tmp=str(tmp_path), tolerance_s=180)
    assert state not in ("down", "healthy"), "D4: wedged must not masquerade as either"
    assert state == "wedged"


def test_d5_an_unreadable_probe_is_unknown_not_fine(tmp_path):
    """A4: claim neither direction when the probe cannot tell."""
    state, detail = daemon_state.rearm_backlog_state(
        "claude", tmp=str(tmp_path / "does-not-exist"), tolerance_s=180)
    assert state in ("unknown", "working"), detail
    if state == "unknown":
        assert "unknown" in detail.lower() or "cannot" in detail.lower()


def test_only_this_agents_triggers_count(tmp_path):
    """A wedge is per-agent: deepseek's backlog must never indict claude's daemon."""
    _trigger(tmp_path, "deepseek", "s9", age_s=900)
    state, _ = daemon_state.rearm_backlog_state("claude", tmp=str(tmp_path), tolerance_s=180)
    assert state == "working"
