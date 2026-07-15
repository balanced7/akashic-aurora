"""AUTOPILOT A1 PRE-REGISTERED ACCEPTANCE -- the core that retires the arm chore.

Spec: research/reviewed/presence-autopilot-reconciliation-2026-07-15.md slice A1
(claude builds, deepseek verifies; rides T075 gamma-scope). Daniel directive
verbatim in note presence-autopilot-directive.

Pins (deepseek's A1-P* numbering, amended by rulings R1/R2):
  P1  daemon_is_live(agent): True while <ns>:daemon:<agent> exists, False after.
  P2  stop-hook fast-path PREDICATE: daemon live -> (pass, provenance line,
      rearm trigger written when the session's listener seat is absent);
      daemon down -> legacy verdict unchanged + the nag latches ONCE per session.
  P3  .rearm plumbing: write_rearm_trigger -> consume_rearms sees exactly the
      agent's own triggers, invokes spawn_fn per sid, clears the file (crash-safe:
      a bad spawn leaves the trigger for the next tick).
  P4  marker sweep honors ruling R1: removed ONLY when no matching .pid seat AND
      age > 24h; a stale-marker-WITH-seat (today's live 46m-idle session) and a
      fresh marker both SURVIVE.
  P5  card runtimes field: build_runtimes renders live/down per child.

Run: py -m pytest tests/test_autopilot_a1.py -q   (no live Redis needed)
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.comm import daemon_state as ds
except ImportError:
    ds = None

from core.comm import wake_seat


def _built():
    assert ds is not None, \
        "A1 build target core/comm/daemon_state.py does not exist yet (RED until built)"


class FakeRedis:
    def __init__(self):
        self.kv = {}
    def set(self, k, v, ex=None, nx=False):
        if nx and k in self.kv:
            return None
        self.kv[k] = v
        return True
    def get(self, k):
        return self.kv.get(k)
    def delete(self, k):
        self.kv.pop(k, None)
    def exists(self, k):
        return 1 if k in self.kv else 0


AGENT = "a1drill"
SID = "aaaabbbb-1111-2222-3333-444455556666"


# --------------------------------------------------------------- P1
def test_p1_daemon_is_live():
    _built()
    c = FakeRedis()
    assert ds.daemon_is_live(AGENT, c=c, ns="bifrost") is False
    c.set(f"bifrost:daemon:{AGENT}", "{}")
    assert ds.daemon_is_live(AGENT, c=c, ns="bifrost") is True
    c.delete(f"bifrost:daemon:{AGENT}")
    assert ds.daemon_is_live(AGENT, c=c, ns="bifrost") is False


# --------------------------------------------------------------- P2
def test_p2_fast_path_predicate_daemon_live(tmp_path):
    _built()
    c = FakeRedis()
    c.set(f"bifrost:daemon:{AGENT}", "{}")
    verdict = ds.stop_hook_wake_verdict(AGENT, SID, c=c, ns="bifrost", tmp=str(tmp_path))
    assert verdict["pass"] is True, "P2: live daemon means the hook never blocks"
    assert "daemon" in verdict["line"].lower()
    assert os.path.exists(ds.rearm_path(AGENT, SID, tmp=str(tmp_path))), \
        "P2: absent listener seat -> the hook leaves a .rearm trigger for the daemon"
    # seat present -> no duplicate trigger needed
    with open(wake_seat.seat_path(AGENT, SID, str(tmp_path)), "w") as f:
        f.write("123")
    os.remove(ds.rearm_path(AGENT, SID, tmp=str(tmp_path)))
    verdict2 = ds.stop_hook_wake_verdict(AGENT, SID, c=c, ns="bifrost", tmp=str(tmp_path))
    assert verdict2["pass"] is True
    assert not os.path.exists(ds.rearm_path(AGENT, SID, tmp=str(tmp_path))), \
        "P2: a seated listener needs no rearm trigger"


def test_p2_daemon_down_legacy_with_latched_nag(tmp_path):
    _built()
    c = FakeRedis()
    v1 = ds.stop_hook_wake_verdict(AGENT, SID, c=c, ns="bifrost", tmp=str(tmp_path))
    assert v1["pass"] is False, "P2: daemon down -> legacy path decides (not the fast path)"
    assert v1.get("nag"), "P2: first firing nags 'start the daemon'"
    v2 = ds.stop_hook_wake_verdict(AGENT, SID, c=c, ns="bifrost", tmp=str(tmp_path))
    assert not v2.get("nag"), "P2: the nag is LATCHED once per session (nudge, never spam)"


# --------------------------------------------------------------- P3
def test_p3_rearm_write_consume_clear(tmp_path):
    _built()
    tmp = str(tmp_path)
    ds.write_rearm_trigger(AGENT, SID, tmp=tmp)
    ds.write_rearm_trigger("otheragent", SID, tmp=tmp)   # foreign trigger stays
    spawned = []
    n = ds.consume_rearms(AGENT, lambda sid: spawned.append(sid) or True, tmp=tmp)
    assert n == 1 and spawned == [SID], "P3: exactly own agent's triggers consumed"
    assert not os.path.exists(ds.rearm_path(AGENT, SID, tmp=tmp)), "P3: consumed -> cleared"
    assert os.path.exists(ds.rearm_path("otheragent", SID, tmp=tmp)), \
        "P3: another agent's trigger untouched"


def test_p3_failed_spawn_keeps_trigger(tmp_path):
    _built()
    tmp = str(tmp_path)
    ds.write_rearm_trigger(AGENT, SID, tmp=tmp)
    ds.consume_rearms(AGENT, lambda sid: False, tmp=tmp)   # spawn refused
    assert os.path.exists(ds.rearm_path(AGENT, SID, tmp=tmp)), \
        "P3: a failed spawn leaves the trigger for the next tick (crash-safe)"


# --------------------------------------------------------------- P4 (ruling R1)
def test_p4_marker_sweep_seat_aware_and_age_gated(tmp_path):
    _built()
    tmp = str(tmp_path)
    old = time.time() - 25 * 3600
    # (a) stale marker, NO seat -> swept
    wake_seat.touch_activity(AGENT, "dead0000-sid", tmp)
    os.utime(wake_seat.activity_marker_path(AGENT, "dead0000-sid", tmp), (old, old))
    # (b) stale marker WITH live seat (today's 46m-idle live session) -> SURVIVES
    wake_seat.touch_activity(AGENT, "idle0000-sid", tmp)
    os.utime(wake_seat.activity_marker_path(AGENT, "idle0000-sid", tmp), (old, old))
    with open(wake_seat.seat_path(AGENT, "idle0000-sid", tmp), "w") as f:
        f.write("321")
    # (c) fresh marker, no seat -> survives (age gate)
    wake_seat.touch_activity(AGENT, "fresh000-sid", tmp)
    removed = ds.sweep_stale_markers(AGENT, tmp=tmp)
    assert removed == 1, f"P4: exactly the seatless 25h marker goes (got {removed})"
    assert not os.path.exists(wake_seat.activity_marker_path(AGENT, "dead0000-sid", tmp))
    assert os.path.exists(wake_seat.activity_marker_path(AGENT, "idle0000-sid", tmp)), \
        "P4/R1: stale-with-seat = idle-but-alive session, NEVER swept"
    assert os.path.exists(wake_seat.activity_marker_path(AGENT, "fresh000-sid", tmp))


# --------------------------------------------------------------- P5
def test_p5_runtimes_card_field():
    _built()
    class Child:
        def __init__(self, alive, tripped=False):
            self.alive, self.tripped = alive, tripped
    r = ds.build_runtimes({"runner": Child(True), "listener": Child(False)})
    assert r == {"runner": "live", "listener": "down"}
    r2 = ds.build_runtimes({"runner": Child(False, tripped=True)})
    assert r2 == {"runner": "blocked"}, "P5: a tripped breaker renders 'blocked', not 'down'"
