"""A1 -- A RUNNER THAT KNOWS IT IS STALE RESTARTS ITSELF. RED first (M3).

THE WASTE, measured across one day (2026-07-28): every fix took HOURS to reach
the processes that needed it. The fleet ran 29+ commits behind while its own
fixes landed; deepseek's census detail was destroyed a SECOND time by a bug
already fixed in git; T113 was announced live and both peer probes still
clipped. T114 gave heartbeats a code stamp and T116 gave the doctor a
retroactive detector -- visibility without remediation, which this arc has
repeatedly named as half an organ. This slice is the other half.

THE CEREMONY, between turns only: at the idle point the runner compares its own
stamp to HEAD. Provably stale by N+ commits, past a minimum-uptime cooldown,
nothing in flight -> respawn with the SAME argv and environment, then stand
down; the runner-lock's existing generation fencing performs the takeover
exactly as it does for a crash. Planned succession rides the machinery already
trusted for unplanned succession -- no new supervision protocol.

FAIL DIRECTION IS KEEP-RUNNING. A restart is for PROVEN staleness: unknown
stamp, unreadable git, any exception -> stay up. A false restart costs a turn
and a cache; a missed restart costs only what today already cost -- and the
doctor still shows the STALE-CODE line either way, so nothing is hidden.

  P1  PROVABLY STALE + PAST COOLDOWN + IDLE -> a reason, naming stamp/head/count.
  P2  AT HEAD -> None (no wolf; this arc has paid for false pages all day).
  P3  INSIDE MIN-UPTIME -> None even if stale (no thrash-loop: a restart that
      re-triggers on boot would flap forever on a busy repo).
  P4  WORK IN FLIGHT -> None (the turn boundary IS the safe point; advisory
      locks self-release at reply, so idle means lock-free).
  P5  UNKNOWN STALENESS -> None. Restarts are for proven staleness; absence of
      evidence keeps the process up (the T116 P5/P6 rule, applied to action).
  P6  THE RESPAWN CARRIES THE SAME ARGV AND THE LANE ENV. The 6.5h LANE STALL
      page happened because a relaunch dropped BIFROST_CONSUME_LANE; that
      lesson is a pin here, not a hope.
  P7  THE DIAL TURNS OFF (AKASHIC_SELF_RESTART=0 -> always None).
  P8  NEVER RAISES. This runs at every turn boundary on every runner.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import self_restart as SR


@pytest.fixture(autouse=True)
def _env():
    saved = {k: os.environ.get(k) for k in
             ("AKASHIC_SELF_RESTART", "AKASHIC_SELF_RESTART_MIN_BEHIND",
              "AKASHIC_SELF_RESTART_MIN_UPTIME_S", "BIFROST_CONSUME_LANE")}
    yield
    for k, v in saved.items():
        os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


def _decide(*, stamped="a" * 12, head="b" * 12, behind=7, uptime_s=3600,
            in_flight=False):
    return SR.should_restart(
        stamped_sha=stamped, head_sha=head, commits_behind=behind,
        uptime_s=uptime_s, in_flight=in_flight)


# --------------------------------------------------------------- P1
def test_p1_provably_stale_past_cooldown_idle_restarts():
    reason = _decide()
    assert reason, "7 commits behind, 1h uptime, idle -- the ceremony must fire"
    for frag in ("aaaaaaaaaaaa", "bbbbbbbbbbbb", "7"):
        assert frag in reason, (
            f"the reason must NAME stamp/head/count -- a restart nobody can explain "
            f"is a crash with better manners: {reason!r}")


# --------------------------------------------------------------- P2
def test_p2_at_head_never_restarts():
    assert _decide(stamped="c" * 12, head="c" * 12, behind=0) is None


# --------------------------------------------------------------- P3
def test_p3_inside_min_uptime_never_restarts():
    assert _decide(uptime_s=30) is None, (
        "a restart that re-triggers on boot flaps forever on a busy repo -- "
        "the cooldown is the anti-thrash guarantee")


# --------------------------------------------------------------- P4
def test_p4_work_in_flight_never_restarts():
    assert _decide(in_flight=True) is None


# --------------------------------------------------------------- P5
def test_p5_unknown_staleness_keeps_running():
    assert _decide(stamped="", head="b" * 12) is None, "no stamp -> no restart"
    assert _decide(stamped="a" * 12, head="") is None, "no HEAD -> no restart"
    assert _decide(behind=0, stamped="a" * 12, head="b" * 12) is None, (
        "stamp differs but the count is unproven -> keep running; restarts are "
        "for PROVEN staleness")


# --------------------------------------------------------------- P6
def test_p6_the_respawn_carries_argv_and_the_lane_env(monkeypatch):
    """The 6.5h LANE STALL happened because a relaunch dropped the lane env."""
    captured = {}

    def _fake_popen(argv, **kw):
        captured["argv"] = list(argv)
        captured["env"] = dict(kw.get("env") or os.environ)
        class _P:
            pid = 99999
        return _P()

    monkeypatch.setattr(SR.subprocess, "Popen", _fake_popen)
    os.environ["BIFROST_CONSUME_LANE"] = "work"
    ok = SR.respawn_self(argv=["scripts/bifrost_runner_deepseek.py",
                               "--agent", "deepseek", "--session", "abc123"])
    assert ok, "respawn must report success when the spawn succeeded"
    assert captured["argv"][0] == sys.executable
    assert "--session" in captured["argv"] and "abc123" in captured["argv"], (
        f"SAME argv or the incarnation changes and the per-incarnation cursor "
        f"forks: {captured['argv']}")
    assert captured["env"].get("BIFROST_CONSUME_LANE") == "work", (
        "the lane env MUST survive the respawn -- this exact omission cost a "
        "6.5h lane stall once already")


# --------------------------------------------------------------- P7
def test_p7_the_dial_turns_off():
    os.environ["AKASHIC_SELF_RESTART"] = "0"
    assert _decide() is None


# --------------------------------------------------------------- P8
def test_p8_never_raises(monkeypatch):
    monkeypatch.setattr(SR, "_min_behind", lambda: (_ for _ in ()).throw(RuntimeError()))
    assert SR.should_restart(stamped_sha="a", head_sha="b", commits_behind=9,
                             uptime_s=9999, in_flight=False) is None


# --------------------------------------------------------------- P9 the frozen-HEAD trap
def test_p9_the_head_the_ceremony_compares_against_is_fresh(monkeypatch):
    """Caught during wiring, before any fence: runtime_age.head_sha() caches per
    process -- correct for the doctor's fresh probe children, FATAL here. A runner
    that boots at HEAD X and calls gather() every loop beat would freeze HEAD at X
    and the ceremony would never fire: the self-restart feature would itself be the
    day's disease (an instrument frozen at its own birth). gather() must re-resolve
    HEAD on a short TTL, not inherit a process-lifetime cache."""
    calls = []

    def _fake_git_head():
        calls.append(1)
        return "f" * 12 if len(calls) > 1 else "e" * 12

    monkeypatch.setattr(SR, "_resolve_head_fresh", _fake_git_head)
    SR._HEAD_CACHE.update({"sha": "", "at": 0.0})
    first = SR.fresh_head_sha()
    SR._HEAD_CACHE["at"] = 0.0                    # force TTL expiry
    second = SR.fresh_head_sha()
    assert first == "e" * 12 and second == "f" * 12, (
        f"HEAD must MOVE for a long-lived process: {first!r} -> {second!r}. A "
        f"process-lifetime cache freezes the ceremony at boot and it never fires.")
