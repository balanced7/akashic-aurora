"""T086 S1/S2a pins: session tombstone + renewal-primacy in the seat-freeing ladder.

Cites research/reviewed/t086-seat-reconciliation-2026-07-16.md (build spec). Exhibit A =
C1-5 (2026-07-16 morning): an ended session's armed watchers held the wake seat; killing
them RESURRECTED the session; then a dead holder's claim blocked the live seat ~30 min
because a live listener pid outranked a 192-minute-stale renewal marker. These pins make
each leg of that chain unrepresentable. Live-Redis pattern (rb21/t083 lineage): unique
agent id per test = namespace isolation; teardown deletes touched keys.
"""
import json
import os
import subprocess
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import runner_lock, session_exit, wake_seat
from core.comm.bus import Bus

try:
    _ONLINE = bool(Bus("t086-probe").online)
except Exception:
    _ONLINE = False

pytestmark = pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline")

GRACE, STALE = 300, 900
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture()
def agent():
    aid = f"t086s1-{uuid.uuid4().hex[:8]}"
    yield aid
    c = runner_lock._client()
    if c is not None:
        try:
            c.delete(f"bifrost:runner:{aid}")
            c.delete(f"bifrost:generation:{aid}")
        except Exception:
            pass


@pytest.fixture()
def sid():
    s = f"t086sid{uuid.uuid4().hex[:10]}"
    yield s
    c = runner_lock._client()
    if c is not None:
        try:
            c.delete(f"bifrost:session:ended:{s}")
        except Exception:
            pass
    try:
        os.remove(wake_seat.tombstone_path(s))
    except Exception:
        pass


def _claim(agent, sid):
    ok, gen, _ = runner_lock.claim_consumer(agent, f"session:{sid}")
    assert ok
    return f"session:{sid}"


# ---------------------------------------------------------------- S1a: tombstone beats grace
def test_tombstoned_holder_freed_instantly_no_grace(agent, sid, tmp_path):
    """The ladder's fast path: a tombstoned session's claim frees IMMEDIATELY -- even
    inside the grace window that protects every other fresh claim."""
    _claim(agent, sid)
    assert wake_seat.write_tombstone(sid, str(tmp_path))
    v = runner_lock.free_if_dead(agent, tmp=str(tmp_path))   # now ~= claim ts -> age ~0
    assert v["freed"] and v["reason"].startswith("session-tombstoned")
    assert runner_lock.holder(agent) is None


def test_fresh_claim_without_tombstone_still_graced(agent, sid, tmp_path):
    """Control: absent a tombstone, grace protects exactly as before (C1-1 behavior kept)."""
    _claim(agent, sid)
    v = runner_lock.free_if_dead(agent, tmp=str(tmp_path))
    assert not v["freed"] and v["reason"].startswith("grace")


def test_clean_death_writes_tombstone(agent, sid, tmp_path):
    """clean_death leg 0: SessionEnd leaves the discriminator behind, first."""
    out = session_exit.clean_death(agent, sid, tmp=str(tmp_path))
    assert out.get("tombstone") is True
    assert wake_seat.is_tombstoned(sid, str(tmp_path))


# ---------------------------------------------------------------- S1b: resurrection breakers
def test_reap_decision_kills_tombstoned_watcher():
    """Janitor: a tombstoned session's live watcher is reaped even with a FRESH marker
    (marker freshness proves the host fired hooks recently -- not that the session lives)."""
    action, reason = wake_seat.reap_decision(
        "someothersid", pid=4242, pid_alive=True, pid_is_watcher=True,
        marker_age_min=1.0, fresh_min=30.0, chain_fn=lambda: (True, "chain intact"),
        my_session="mysid", tombstoned=True)
    assert action == "kill" and "session-tombstoned" in reason


def test_stop_hook_stands_down_for_tombstoned_session(sid):
    """The resurrection-loop breaker, exercised through the REAL hook: a turn ending in a
    tombstoned session gets NO block demand and touches nothing. (Replay of this morning:
    the ghost's stop hook would have demanded re-arming; now it stands down by record.)"""
    assert wake_seat.write_tombstone(sid)   # default tempdir -- where the hook looks
    payload = json.dumps({"session_id": sid, "hook_event_name": "Stop"})
    r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "hooks", "claude_stop.py")],
                       input=payload, capture_output=True, text=True, timeout=60, cwd=REPO)
    assert '"decision": "block"' not in (r.stdout or "")
    assert "tombstoned" in (r.stderr or "")
    marker = wake_seat.activity_marker_path(os.getenv("AKASHIC_AGENT_ID") or "claude", sid)
    assert not os.path.exists(marker), "a tombstoned resurrection must not fake renewal"


# ---------------------------------------------------------------- S2a: renewal primacy
def test_stale_marker_beats_live_listener(agent, sid, tmp_path):
    """THE ca9a86ad pin: renewal-stale (marker >= stale_s) frees the seat even though the
    listener pid is alive. Process liveness is not session liveness."""
    _claim(agent, sid)
    seat = wake_seat.seat_path(agent, sid, str(tmp_path))
    open(seat, "w").write("99999")
    marker = wake_seat.activity_marker_path(agent, sid, str(tmp_path))
    open(marker, "w").write("x")                     # mtime = real now
    aged_now = time.time() + STALE + 60              # marker_age ~= STALE+60; claim age same
    v = runner_lock.free_if_dead(agent, now=aged_now, tmp=str(tmp_path),
                                 pid_alive=lambda p: True)
    assert v["freed"] and v["reason"].startswith("renewal-stale")


def test_midband_marker_live_listener_still_alive(agent, sid, tmp_path):
    """Conservative mid-band preserved: grace < marker age < stale + live listener = ALIVE
    (an idle-but-live session inside the lease window keeps its seat)."""
    _claim(agent, sid)
    seat = wake_seat.seat_path(agent, sid, str(tmp_path))
    open(seat, "w").write("99999")
    marker = wake_seat.activity_marker_path(agent, sid, str(tmp_path))
    open(marker, "w").write("x")
    mid_now = time.time() + GRACE + 100              # marker_age ~= 400s: mid-band
    v = runner_lock.free_if_dead(agent, now=mid_now, tmp=str(tmp_path),
                                 pid_alive=lambda p: True)
    assert not v["freed"] and v["reason"].startswith("listener-alive")


# ---------------------------------------------------------------- S1c: fail-open
def test_tombstone_probe_error_fails_open(agent, sid, tmp_path, monkeypatch):
    """A raising tombstone probe changes NOTHING: fresh claim stays graced, no crash."""
    _claim(agent, sid)
    monkeypatch.setattr(wake_seat, "is_tombstoned",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("probe down")))
    v = runner_lock.free_if_dead(agent, tmp=str(tmp_path))
    assert not v["freed"] and v["reason"].startswith("grace")


def test_kill_switch_disables_tombstones(sid, tmp_path, monkeypatch):
    """AKASHIC_TOMBSTONE=0: write refuses, read says False even with a tomb file present."""
    open(wake_seat.tombstone_path(sid, str(tmp_path)), "w").write("x")
    monkeypatch.setenv("AKASHIC_TOMBSTONE", "0")
    assert not wake_seat.write_tombstone(sid, str(tmp_path))
    assert not wake_seat.is_tombstoned(sid, str(tmp_path))
