"""T083-C1-1 pins: free a consumer seat whose SESSION holder is PROVABLY dead (crash net, fast leg).

clean_death frees the seat on graceful SessionEnd; a crash-killed session leaves it to TTL
(live receipt 2026-07-15: ~17 min blocked). free_if_dead probes the evidence ladder --
activity-marker freshness, armed-listener pid, no-evidence staleness -- and frees ONLY on
positive death evidence; every ambiguity resolves toward ALIVE. Live-Redis pins (rb21 pattern):
unique agent id per test = namespace isolation; teardown deletes touched keys.
"""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import runner_lock, wake_seat
from core.comm.bus import Bus

try:
    _ONLINE = bool(Bus("t083-probe").online)
except Exception:
    _ONLINE = False

pytestmark = pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline")

GRACE, STALE = 300, 900


@pytest.fixture()
def agent():
    aid = f"t083c1-{uuid.uuid4().hex[:8]}"
    yield aid
    c = runner_lock._client()
    if c is not None:
        try:
            c.delete(f"bifrost:runner:{aid}")
            c.delete(f"bifrost:generation:{aid}")
        except Exception:
            pass


def _claim(agent, sid="deadbeef01"):
    tok = f"session:{sid}"
    ok, gen, _ = runner_lock.claim_consumer(agent, tok)
    assert ok
    return tok


def _aged(agent):
    """A now= far past the claim ts, so the grace gate passes without sleeping."""
    rec = runner_lock.holder(agent)
    return runner_lock._ts_epoch(rec["ts"], default=time.time()) + GRACE + 100


def test_no_holder_is_noop(agent):
    v = runner_lock.free_if_dead(agent)
    assert v == {"freed": False, "reason": "no-holder", "holder": None}


def test_runner_token_never_touched(agent):
    ok = runner_lock.acquire(agent, f"{agent}:1234:aabbcc")   # a runner-style token
    assert ok
    v = runner_lock.free_if_dead(agent, now=time.time() + 10_000)
    assert not v["freed"] and v["reason"] == "holder-is-runner"
    assert runner_lock.holder(agent) is not None


def test_fresh_claim_protected_by_grace(agent):
    _claim(agent)
    v = runner_lock.free_if_dead(agent)          # now ~= claim ts -> age ~0
    assert not v["freed"] and v["reason"].startswith("grace")


def test_fresh_activity_marker_means_alive(agent, tmp_path):
    tok = _claim(agent, sid="s1")
    m = wake_seat.activity_marker_path(agent, "s1", str(tmp_path))
    open(m, "w").write("x")                       # mtime = now; marker fresh vs aged now?
    now = _aged(agent)
    os.utime(m, (now - 10, now - 10))             # touched 10s before probe time
    v = runner_lock.free_if_dead(agent, now=now, tmp=str(tmp_path))
    assert not v["freed"] and v["reason"].startswith("marker-fresh")
    assert runner_lock.holder(agent)["token"] == tok


def test_dead_listener_pid_frees_the_seat(agent, tmp_path):
    _claim(agent, sid="s2")
    open(wake_seat.seat_path(agent, "s2", str(tmp_path)), "w").write("999999")
    v = runner_lock.free_if_dead(agent, now=_aged(agent), tmp=str(tmp_path),
                                 pid_alive=lambda p: False)
    assert v["freed"] and "listener-pid-dead" in v["reason"]
    assert runner_lock.holder(agent) is None      # seat claimable again
    ok, _, _ = runner_lock.claim_consumer(agent, "session:successor")
    assert ok                                     # the successor claims cleanly


def test_live_listener_pid_means_alive(agent, tmp_path):
    _claim(agent, sid="s3")
    open(wake_seat.seat_path(agent, "s3", str(tmp_path)), "w").write(str(os.getpid()))
    v = runner_lock.free_if_dead(agent, now=_aged(agent), tmp=str(tmp_path),
                                 pid_alive=lambda p: True)
    assert not v["freed"] and v["reason"].startswith("listener-alive")


def test_no_evidence_at_all_frees(agent, tmp_path):
    _claim(agent, sid="s4")                       # no seat file, no marker in tmp
    v = runner_lock.free_if_dead(agent, now=_aged(agent), tmp=str(tmp_path))
    assert v["freed"] and "no-liveness-evidence" in v["reason"]


def test_stale_marker_frees(agent, tmp_path):
    _claim(agent, sid="s5")
    m = wake_seat.activity_marker_path(agent, "s5", str(tmp_path))
    open(m, "w").write("x")
    now = _aged(agent)
    os.utime(m, (now - STALE - 60, now - STALE - 60))
    v = runner_lock.free_if_dead(agent, now=now, tmp=str(tmp_path))
    assert v["freed"] and "marker-stale" in v["reason"]


def test_midband_marker_is_indeterminate_ttl_rules(agent, tmp_path):
    _claim(agent, sid="s6")
    m = wake_seat.activity_marker_path(agent, "s6", str(tmp_path))
    open(m, "w").write("x")
    now = _aged(agent)
    os.utime(m, (now - (GRACE + 60), now - (GRACE + 60)))   # between grace and stale
    v = runner_lock.free_if_dead(agent, now=now, tmp=str(tmp_path))
    assert not v["freed"] and v["reason"].startswith("indeterminate")


def test_probe_error_fails_toward_alive(agent, tmp_path):
    _claim(agent, sid="s7")
    open(wake_seat.seat_path(agent, "s7", str(tmp_path)), "w").write("4242")
    v = runner_lock.free_if_dead(agent, now=_aged(agent), tmp=str(tmp_path),
                                 pid_alive=lambda p: 1 / 0)
    assert not v["freed"]                          # an erroring probe never frees
    assert runner_lock.holder(agent) is not None
