"""
RB-3 (T029, demoted scope) -- drainer liveness signal, observe-only.

Both fenced batteries ranked drainer-death top-5; verification demoted it: the catastrophic
re-wedge is already defended (errors="replace" + blanket except + finally: pipe.close()), so
the residual risk is a SILENTLY frozen diagnostic tail while the child still runs, plus an
exit-flush join timeout that can feed exit classification a partial tail. This pins the
flag, not a watchdog: a stopped drainer on a live child raises registry-visible state within
one monitor tick; the flag clears at exit flush; a timed-out flush is recorded.

Run: py -m pytest tests/test_launcher_drainer_liveness.py -q
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.comm.launcher as launcher_mod
from core.comm.launcher import AgentProcess, AgentSpec, Launcher


def _dead_thread(name="drain-x-stdout"):
    t = threading.Thread(target=lambda: None, name=name)
    t.start()
    t.join()
    return t


def _stuck_thread(evt, name="drain-x-stderr"):
    t = threading.Thread(target=evt.wait, daemon=True, name=name)
    t.start()
    return t


def _quiet_launcher(monkeypatch):
    l = Launcher()
    notes = []
    monkeypatch.setattr(l, "_bus_note", lambda text: notes.append(text))
    return l, notes


def test_dead_drainer_on_live_child_raises_flag(monkeypatch):
    l, notes = _quiet_launcher(monkeypatch)
    proc = AgentProcess(agent_id="x", pid=123, status="running", drainers=[_dead_thread()])
    l._flag_dead_drainers(proc)
    assert proc.drainer_dead is True, "dead drainer + live child = the risk state, flagged"
    assert len(notes) == 1 and "drain" in notes[0], "exactly one supervisor note"
    l._flag_dead_drainers(proc)
    assert len(notes) == 1, "flag is once-only -- no note spam on later ticks"


def test_live_drainers_do_not_flag(monkeypatch):
    l, notes = _quiet_launcher(monkeypatch)
    evt = threading.Event()
    proc = AgentProcess(agent_id="x", status="running", drainers=[_stuck_thread(evt)])
    l._flag_dead_drainers(proc)
    evt.set()
    assert proc.drainer_dead is False and notes == []


def test_exit_flush_clears_flag_and_is_clean_for_dead_drainers(monkeypatch):
    l, _ = _quiet_launcher(monkeypatch)
    proc = AgentProcess(agent_id="x", drainers=[_dead_thread()], drainer_dead=True)
    l._flush_drainers(proc)
    assert proc.drainer_dead is False, "at exit the risk state no longer applies -- flag clears"
    assert proc.drain_flush_timeout is False


def test_exit_flush_timeout_is_recorded(monkeypatch):
    monkeypatch.setattr(launcher_mod, "DRAIN_FLUSH_JOIN_SEC", 0.05)
    l, _ = _quiet_launcher(monkeypatch)
    evt = threading.Event()
    proc = AgentProcess(agent_id="x", drainers=[_stuck_thread(evt)])
    l._flush_drainers(proc)
    evt.set()
    assert proc.drain_flush_timeout is True, \
        "a flush that outlives the join window is recorded -- the exit tail may be partial"


def test_registry_surfaces_drainer_state(monkeypatch):
    l, _ = _quiet_launcher(monkeypatch)
    monkeypatch.setattr(l, "_reload", lambda: None)
    monkeypatch.setattr(l, "_armed_set", lambda: set())
    l._specs = {"x": AgentSpec(agent_id="x", runtime="python_runner",
                               description="", command=["py"])}
    l._procs = {"x": AgentProcess(agent_id="x", status="running",
                                  drainer_dead=True, drain_flush_timeout=True)}
    row = next(r for r in l.registry() if r["agent_id"] == "x")
    assert row["drainer_dead"] is True and row["drain_flush_timeout"] is True
