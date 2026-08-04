"""PRE-REGISTERED ACCEPTANCE (T147) -- a live runner must not render DEAD.

SEASON 0, the load lab. Before twenty seats can compete, the fleet has to be able to tell which
seats are alive. Today it cannot, for exactly the seat class Season 1 wants twenty of.

MEASURED ON LIVE KEYS 2026-08-04. There are two worklive key shapes and nothing bridges them:

    runners write   bifrost:worklive:<agent>           (bare)
    roster reads    bifrost:worklive:<agent>#<sid8>    (per-incarnation, roster.py:49)

roster.py records the split in its own header at lines 8-9 -- "deepseek and kimi runners beat
bifrost:worklive:<agent>, but seats had nothing per-incarnation" -- and it was never closed.
Proof, with the kimi runner alive at pid 10608 and beating its bare key every ~40s:

    $ py agent_cli.py roster | grep kimi
      [DEAD ] kimi#51a77a23   phase=sync   beat=8790.9s

    >>> reaper._provably_dead(row) -> True        # and True for every deepseek seat too

roster.py:9 calls the roster "the reaper's only sensor". So a live runner's directed mail is
eligible for re-homing, and the sensor that decides is blind to it.

THIS IS THE SECOND HALF OF A FIX THAT ONLY EVER LANDED ON ONE SIDE. tests/test_s2_roster.py was
written because "TONIGHT NO CLAUDE SEAT PUBLISHES A HEARTBEAT AT ALL". That closed the harness
side; roster.heartbeat's production callers are still only agent/bifrost_pull.py and
agent/harness/hooks/*. No runner has ever called it.

AND THE RUNNER'S OWN COMMENT DESCRIBES THE BUG IT HAS. bifrost_runner_deepseek.py, above the
heartbeat thread: "Without this, a long reply ... would let presence expire -- the agent vanishes
from the roster though it's alive." The intent was right; the thread refreshes the BARE key and
bus.register, neither of which writes what the roster renders. The stated goal was never achieved.

WHAT IS NOT THE FIX, recorded so it is not re-proposed: do NOT weaken the lock or the reaper. I
filed W125 arguing the runner lock should steal on a stale heartbeat; runner_lock.py:93 already
rejects that in writing -- "a recycled pid or a paused process would let it evict a LIVE holder and
produce the split-brain this lock exists to prevent." The lock was correct every time it refused
me. W126 is that correction.

  R1  a runner-shaped beat renders the seat LIVE
  R2  a beating seat is NOT provably_dead              (the reaper consequence)
  R3  EVERY scripts/bifrost_runner_*.py calls roster.heartbeat   (enumerated from disk, not listed)
  R4  the bare worklive refresh survives                (other readers still depend on it)
  R5  a broken client never raises                      (a heartbeat must never kill the loop)

Run: py -m pytest tests/test_t147_runner_seats_are_visible.py -q
"""
import os
import re
import sys
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import reaper, roster as R  # noqa: E402

NS = f"t147{uuid.uuid4().hex[:8]}"
AGENT = "deepseek-probe"
SID = "cdfb9126aaaa"


def _client():
    c = R._connect()
    if c is None:
        pytest.skip("redis unavailable")
    return c


def test_r1_a_runner_shaped_beat_renders_live():
    c = _client()
    assert R.heartbeat(NS, AGENT, SID, phase="handling", client=c)["ok"] is True
    rows = [r for r in R.roster(NS, client=c) if str(r.get("seat", "")).startswith(AGENT)]
    assert rows, "a beating runner produced no roster row at all"
    assert rows[0]["state"] == "LIVE", (
        f"a runner that just beat renders {rows[0]['state']} -- the roster is the reaper's "
        f"only sensor and it cannot see this seat class")


def test_r2_a_beating_seat_is_not_provably_dead():
    """The consequence that matters. reaper._provably_dead returned True for the LIVE kimi
    runner and for every deepseek seat on 2026-08-04."""
    c = _client()
    R.heartbeat(NS, AGENT, SID, phase="handling", client=c)
    rows = [r for r in R.roster(NS, client=c) if str(r.get("seat", "")).startswith(AGENT)]
    assert rows
    assert reaper._provably_dead(rows[0], client=c, ns=NS) is False, (
        "a live runner's directed mail is eligible for re-homing")


def test_r3_every_runner_publishes_the_seat_beat():
    """STRUCTURAL, and enumerated from disk rather than hand-listed -- the same discipline
    ENTRY_POINTS uses two files over, and the same mistake T146 punished me for. A fix that
    lands in one runner and not its four siblings is not a fix."""
    rd = os.path.join(ROOT, "scripts")
    runners = sorted(f for f in os.listdir(rd)
                     if f.startswith("bifrost_runner_") and f.endswith(".py"))
    assert runners, "no runner scripts found -- the enumeration itself is broken"
    missing = []
    for f in runners:
        src = open(os.path.join(rd, f), encoding="utf-8", errors="replace").read()
        if not re.search(r"roster\.heartbeat\s*\(", src):
            missing.append(f)
    assert not missing, (
        f"{len(missing)} of {len(runners)} runner(s) never publish the per-incarnation beat "
        f"the roster reads, so they render DEAD while alive: {missing}")


def test_r4_the_bare_worklive_refresh_survives():
    """Other readers (doctor, turn_metrics) still consume the bare key. The fix ADDS a beat;
    it must not trade one blind spot for another."""
    rd = os.path.join(ROOT, "scripts")
    runners = sorted(f for f in os.listdir(rd)
                     if f.startswith("bifrost_runner_") and f.endswith(".py"))
    dropped = [f for f in runners
               if not re.search(r"worklive\(", open(os.path.join(rd, f), encoding="utf-8",
                                                    errors="replace").read())]
    assert not dropped, f"runner(s) stopped refreshing the bare worklive key: {dropped}"


def test_r5_a_broken_client_never_raises():
    """roster.heartbeat's docstring promises 'Never raises.' The runner calls it from a daemon
    thread inside a bare except, but the promise is load-bearing and gets pinned."""
    class Broken:
        def get(self, *a, **k):
            raise RuntimeError("redis down")

        def __getattr__(self, _n):
            def _boom(*a, **k):
                raise RuntimeError("redis down")
            return _boom

    got = R.heartbeat(NS, AGENT, SID, client=Broken())   # must not raise
    assert got["ok"] is False
    # NOTE: heartbeat is annotated -> bool but returns {"ok": ..., "resumed_after_s": ...}.
    # An `is not False` assertion would therefore pass on ANY outcome -- my first draft of R1
    # did exactly that and was green while proving nothing. Both pins now read ["ok"].
