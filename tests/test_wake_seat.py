"""T029 Wave 2 pins -- the per-session wake-seat protocol (core/comm/wake_seat.py).

Kill conditions from docs/resilience-battery-2026-07.md sec. 6 + the reconciled K6-K8
(docs/resilience-wave2-seat-design-2026-07.md). Hermetic: fake seats in tmp_path, injected
snapshots, no Redis, no WMI, no processes killed. The one live-drill item (two real
sessions, 3 start/stop cycles) is a runbook, not a pytest -- see the design doc B4.
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import wake_seat as ws


AGENT = "tclaude"          # never collides with a real agent's tempdir files


def _seat(tmp, sid, pid):
    p = ws.seat_path(AGENT, sid, str(tmp))
    with open(p, "w") as f:
        f.write(str(pid))
    return p


def _marker(tmp, sid, age_min):
    p = ws.activity_marker_path(AGENT, sid, str(tmp))
    with open(p, "w") as f:
        f.write(str(time.time() - age_min * 60))
    return p


def _snap(*procs):
    """snapshot from tuples (pid, ppid, name, cmdline, created_ms)."""
    return {p: {"ppid": pp, "name": n, "cmdline": c, "created": cr}
            for p, pp, n, c, cr in procs}


WATCHER_CMD = "python.exe scripts/bifrost_wake.py --agent tclaude"


# ---------------------------------------------------------------- seat namespace (deepseek pin 1, 5, 6)
def test_wake_seat_session_scoped(tmp_path):
    a = ws.seat_path(AGENT, "sidA", str(tmp_path))
    b = ws.seat_path(AGENT, "sidB", str(tmp_path))
    legacy = ws.seat_path(AGENT, None, str(tmp_path))
    assert a != b != legacy and a != legacy, "three distinct seats -- sessions never collide"
    assert legacy.endswith(f"bifrost_wake_{AGENT}.pid"), "legacy path unchanged (pin 6 backward compat)"


def test_iter_seats_scopes_to_exact_agent(tmp_path):
    _seat(tmp_path, "sidA", 111)
    _seat(tmp_path, None, 222)
    other = os.path.join(str(tmp_path), f"bifrost_wake_{AGENT}-2_sidX.pid")   # prefix cousin
    with open(other, "w") as f:
        f.write("333")
    foreign = os.path.join(str(tmp_path), "bifrost_wake_deepseek_sidY.pid")
    with open(foreign, "w") as f:
        f.write("444")
    got = {sid for _, sid in ws.iter_seats(AGENT, str(tmp_path))}
    assert got == {"sidA", None}, "exact-agent scoping: no cousins, no foreign agents (pin 5)"


# ---------------------------------------------------------------- decision table (pure)
def _chain_never():
    raise AssertionError("chain_fn must not be called on this path")


def test_decision_dead_pid_cleans_without_kill():
    action, reason = ws.reap_decision("sidA", 999, False, False, None, 30, _chain_never)
    assert action == "clean" and "dead" in reason


def test_decision_recycled_nonwatcher_cleans():
    action, reason = ws.reap_decision("sidA", 999, True, False, None, 30, _chain_never)
    assert action == "clean" and "recycled" in reason


def test_decision_own_session_skipped():
    action, reason = ws.reap_decision("mine", 999, True, True, None, 30, _chain_never, my_session="mine")
    assert action == "skip" and "own session" in reason


def test_decision_k6_legacy_ghost_killed():
    action, reason = ws.reap_decision(None, 999, True, True, None, 30, _chain_never)
    assert action == "kill" and "K6 migration" in reason


def test_reap_marker_fresh_fast_path():
    """K7 pin 2: a fresh marker decides ALONE -- the chain fn is never consulted."""
    action, reason = ws.reap_decision("sidA", 999, True, True, 2.0, 30, _chain_never)
    assert action == "skip" and "fresh" in reason


def test_reap_idle_but_alive_not_reaped():
    """K7 pin 1: stale marker + live parent chain = idle-but-alive session -> IMMUNE."""
    action, reason = ws.reap_decision("sidA", 999, True, True, 72.0, 30,
                                      lambda: (True, 'parent chain found "claude.exe" pid 7'))
    assert action == "skip" and "K7" in reason and "claude.exe" in reason


def test_reap_both_dead_reaps():
    """K7 pin 3: marker stale AND chain dead -> reap, with BOTH factors in the reason."""
    action, reason = ws.reap_decision("sidA", 999, True, True, 65.0, 30,
                                      lambda: (False, "chain broken at pid 41 (dead)"))
    assert action == "kill" and "65m stale" in reason and "chain broken" in reason


def test_reap_chain_error_is_alive():
    """K8: ANY chain-check failure fails toward alive."""
    def boom():
        raise RuntimeError("wmi exploded")
    action, reason = ws.reap_decision("sidA", 999, True, True, 65.0, 30, boom)
    assert action == "skip" and "assuming alive" in reason and "K8" in reason


def test_reap_missing_marker_defers_to_chain():
    """No marker (pre-upgrade session) never means dead by itself -- the chain decides."""
    action, _ = ws.reap_decision("sidA", 999, True, True, None, 30, lambda: (True, "chain intact"))
    assert action == "skip"
    action, _ = ws.reap_decision("sidA", 999, True, True, None, 30, lambda: (False, "chain broken"))
    assert action == "kill"


# ---------------------------------------------------------------- chain walk
def test_chain_alive_finds_harness_ancestor():
    snap = _snap((10, 20, "python.exe", WATCHER_CMD, 5000),
                 (20, 30, "py.exe", "py", 4000),
                 (30, 40, "powershell.exe", "powershell", 3000),
                 (40, 50, "claude.exe", "claude engine", 2000))
    alive, ev = ws.chain_alive(10, snap)
    assert alive and "claude.exe" in ev


def test_chain_alive_broken_link_is_dead():
    snap = _snap((10, 20, "python.exe", WATCHER_CMD, 5000),
                 (20, 99, "py.exe", "py", 4000))          # ppid 99 not in snapshot
    alive, ev = ws.chain_alive(10, snap)
    assert not alive and "broken" in ev and "99" in ev


def test_chain_alive_recycled_parent_is_dead():
    snap = _snap((10, 20, "python.exe", WATCHER_CMD, 5000),
                 (20, 30, "py.exe", "py", 4000),
                 (30, 40, "powershell.exe", "powershell", 9_999_000))   # younger than child
    alive, ev = ws.chain_alive(10, snap)
    assert not alive and "recycled" in ev


def test_chain_alive_ambiguity_fails_safe():
    snap = _snap((10, 2, "python.exe", WATCHER_CMD, 5000))   # straight to system root
    alive, _ = ws.chain_alive(10, snap)
    assert alive, "walking off the top without contradiction = fail-safe alive (K8 direction)"


# ---------------------------------------------------------------- janitor (integration, injected)
def test_janitor_fresh_marker_never_snapshots(tmp_path):
    """K7 pin 2 at the janitor level: fresh marker -> zero WMI cost, seat untouched."""
    p = _seat(tmp_path, "sidA", 999)
    _marker(tmp_path, "sidA", 2.0)
    def no_snap():
        raise AssertionError("snapshot must not be taken on the fresh fast path")
    res = ws.janitor(AGENT, my_session="me", tmp=str(tmp_path), snapshot_fn=no_snap,
                     kill_fn=lambda pid: pytest.fail("kill on fresh path"))
    assert res == [(p, "skip", res[0][2])] and "fresh" in res[0][2]
    assert os.path.exists(p), "fresh-marker seat survives"


def test_janitor_dead_pid_cleans_file_no_kill(tmp_path):
    p = _seat(tmp_path, "sidA", 999)
    _marker(tmp_path, "sidA", 90.0)
    killed = []
    res = ws.janitor(AGENT, tmp=str(tmp_path), snapshot_fn=lambda: _snap(), kill_fn=killed.append)
    assert res[0][1] == "clean" and not killed and not os.path.exists(p)


def test_janitor_idle_alive_immune_and_logged(tmp_path):
    p = _seat(tmp_path, "sidA", 10)
    _marker(tmp_path, "sidA", 90.0)
    snap = _snap((10, 40, "python.exe", WATCHER_CMD, 5000),
                 (40, 2, "claude.exe", "claude engine", 2000))
    killed = []
    res = ws.janitor(AGENT, tmp=str(tmp_path), snapshot_fn=lambda: snap, kill_fn=killed.append)
    assert res[0][1] == "skip" and "K7" in res[0][2] and not killed and os.path.exists(p)
    log = open(ws.provenance_path(AGENT, str(tmp_path)), encoding="utf-8").read()
    assert "K7" in log, "the immunity decision is auditable from the log alone"


def test_janitor_true_orphan_reaped_with_both_factors(tmp_path):
    p = _seat(tmp_path, "sidA", 10)
    _marker(tmp_path, "sidA", 65.0)
    snap = _snap((10, 99, "python.exe", WATCHER_CMD, 5000))      # parent 99 gone -> chain dead
    killed = []
    res = ws.janitor(AGENT, tmp=str(tmp_path), snapshot_fn=lambda: snap, kill_fn=killed.append)
    assert res[0][1] == "kill" and killed == [10] and not os.path.exists(p)
    log = open(ws.provenance_path(AGENT, str(tmp_path)), encoding="utf-8").read()
    assert "stale" in log and "broken" in log, "provenance carries BOTH factors"


def test_janitor_snapshot_unavailable_is_alive(tmp_path):
    """K8 at the janitor level: no snapshot -> nothing killed, nothing cleaned."""
    p = _seat(tmp_path, "sidA", 10)
    _marker(tmp_path, "sidA", 90.0)
    res = ws.janitor(AGENT, tmp=str(tmp_path), snapshot_fn=lambda: None,
                     kill_fn=lambda pid: pytest.fail("kill without evidence"))
    assert res[0][1] == "skip" and "K8" in res[0][2] and os.path.exists(p)


def test_janitor_k6_legacy_ghost_migrated(tmp_path):
    p = _seat(tmp_path, None, 10)
    snap = _snap((10, 40, "python.exe", WATCHER_CMD, 5000),
                 (40, 2, "claude.exe", "claude engine", 2000))   # chain alive -- K6 kills anyway
    killed = []
    res = ws.janitor(AGENT, tmp=str(tmp_path), snapshot_fn=lambda: snap, kill_fn=killed.append)
    assert res[0][1] == "kill" and "K6" in res[0][2] and killed == [10] and not os.path.exists(p)


# ---------------------------------------------------------------- watcher exit codes (benign = 0)
class _FakeApi:
    """Just enough BifrostAPI for watch(): online, and a scriptable wake_block."""
    online_now = True

    def __init__(self, on_block=None):
        self._on_block = on_block or (lambda: [])

    def online(self):
        return True

    def wake_block(self, timeout_ms=0):
        return self._on_block()


def test_watch_stolen_seat_exits_zero(tmp_path, capsys):
    import scripts.bifrost_wake as bw
    hb = tmp_path / "seat.pid"
    hb.write_text(str(os.getpid()))                       # a different pid owns the seat
    rc = bw.watch(AGENT, 5, 50, api=_FakeApi(), hb_path=str(hb), my_pid=999999, session_id="sidA")
    out = capsys.readouterr().out
    assert rc == 0, "displacement is benign -- no FAILED badge into a live session"
    assert "standing down" in out and "benign" in out, "the printed line is the provenance"


def test_watch_lost_seat_exits_zero_promptly(tmp_path, capsys):
    """Seat-loss is a TRANSITION: a watcher that HELD its seat and finds it gone stands
    down loudly (the sec. 6 flaw-c closure). Seat creation stays main()'s job."""
    import scripts.bifrost_wake as bw
    hb = tmp_path / "seat.pid"
    hb.write_text("999999")                               # armed: the seat is OURS

    def steal_then_quiet():
        if hb.exists():
            hb.unlink()                                   # the seat vanishes mid-watch
        return []

    t0 = time.time()
    rc = bw.watch(AGENT, 30, 50, api=_FakeApi(steal_then_quiet), hb_path=str(hb),
                  my_pid=999999, session_id="sidA")
    out = capsys.readouterr().out
    assert rc == 0 and "seat lost" in out, "seatless watching is impossible -- loud benign exit"
    assert time.time() - t0 < 5, "stand-down is prompt, not deadline-length"


def test_watch_unseated_embedder_keeps_watching(tmp_path):
    """An embedder (tests, library callers) that never seated keeps the pre-Wave-2
    contract: no seat file is written for it and absence does not stand it down."""
    import scripts.bifrost_wake as bw
    hb = tmp_path / "seat.pid"
    rc = bw.watch(AGENT, 1, 50, api=_FakeApi(), hb_path=str(hb), my_pid=424242)
    assert rc == 0 and not hb.exists(), "watch() writes no files it wasn't given"


# ---------------------------------------------------------------- provenance log hygiene
def test_provenance_appends_and_survives(tmp_path):
    ws.append_provenance(AGENT, "first decision", str(tmp_path))
    ws.append_provenance(AGENT, "second decision", str(tmp_path))
    log = open(ws.provenance_path(AGENT, str(tmp_path)), encoding="utf-8").read()
    assert "first decision" in log and "second decision" in log
