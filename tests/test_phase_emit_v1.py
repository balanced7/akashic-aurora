"""W0.2a pins (RED first): Gap 2 -- a seat's phase CHANGES land on the spine, its heartbeat does not.

SPEC: Gap 2 of `research/in-flight/the-record-is-total-map-2026-10-01.md` (Heimdall), folded as
      row W0.2a by `fences/one-spine/reconciliation.md`.

THE SEAM WAS NAMED TWICE, BLIND. Heimdall (half_a) and Rill (half-rill) were asked independently
where a phase change is observable. Both answered `core/comm/liveness.py:146`, the
`if phase != self._phase:` gate inside `set()`, and both independently refused `_flush()` and
`refresh()` because those are the ~5 s heartbeat path. Rill read only the brief and that one
module and said so. Two seats, one line, no contact -- which is the strongest evidence in the
round that the seam is real and not a preference.

WHY THAT LINE AND NOWHERE ELSE. `set()` is the only place that can tell a TRANSITION from a
re-stamp, because it is the only place that compares the incoming phase against the stored one;
`since_ts` moves only inside that branch. An emit in `_flush()` fires on every heartbeat and turns
a 5 s pulse into a per-second firehose. An emit derived by a READER from the worklive record
either misses fast transitions (idle to thinking to idle inside one window) or double-counts them.
The transition must be emitted AT the transition, once, by the process that owns the phase.

WHAT THIS DELIBERATELY DOES NOT DO: `kind='wedge'`. A wedge is the ABSENCE of a `set()` over time,
and the beater never runs while wedged, so it cannot observe its own wedge. That emit belongs to
the watchdog that reads `since_ts` ageing, and both halves say so independently.

ONE PLACEMENT CHOICE THAT DEPARTS FROM THE LETTER OF BOTH HALVES, stated rather than slipped in.
They put the emit inside the `if`, which sits inside `with self._lock:`. Holding a mutex across a
network write serialises every phase change in the process behind one Redis round trip. These pins
require the emit to happen AFTER the lock is released: the SEAM both seats named is the predicate,
and honouring the predicate does not require holding their lock while we do I/O.

Hermetic: the emit function is injected, so nothing here touches Redis.
"""
import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import liveness as L  # noqa: E402


@pytest.fixture
def spy(monkeypatch):
    """Capture every phase emit, and neuter the Redis flush so these run with no store."""
    seen = []
    monkeypatch.setattr(L, "_emit_phase", lambda **kw: seen.append(kw))
    monkeypatch.setattr(L, "_client", lambda: None)      # _flush becomes a no-op
    return seen


def test_a_phase_change_emits_exactly_one_record(spy):
    w = L.WorkLive("t-agent")
    w.set("thinking")
    assert len(spy) == 1
    assert spy[0]["phase"] == "thinking"


def test_the_record_names_what_it_came_from(spy):
    w = L.WorkLive("t-agent")
    w.set("thinking")
    e = spy[0]
    assert e["agent"] == "t-agent"
    assert e["prev"] == "online"                  # the phase it LEFT, or a transition is half a fact
    assert isinstance(e["since_ts"], float)
    assert e["turn"] == 0
    assert "code_sha" in e                        # T114: WHAT is alive, not merely that something is


def test_a_same_phase_set_emits_nothing(spy):
    w = L.WorkLive("t-agent")
    w.set("thinking")
    w.set("thinking", detail="still at it")
    assert len(spy) == 1, "a detail update is not a transition"


def test_the_heartbeat_path_emits_nothing(spy):
    w = L.WorkLive("t-agent")
    w.set("thinking")
    for _ in range(20):
        w.refresh()
    assert len(spy) == 1, "refresh() is the ~5 s re-stamp; emitting there is the firehose Gap 2 forbids"


def test_every_distinct_transition_is_one_record(spy):
    w = L.WorkLive("t-agent")
    for p in ("reading", "thinking", "handling", "idle"):
        w.set(p)
    assert [e["phase"] for e in spy] == ["reading", "thinking", "handling", "idle"]
    assert [e["prev"] for e in spy] == ["online", "reading", "thinking", "handling"]


def test_a_fast_transition_pair_is_not_collapsed(spy):
    # idle -> thinking -> idle inside one heartbeat window. A reader polling the worklive record
    # would see only `idle` and conclude nothing happened.
    w = L.WorkLive("t-agent")
    w.set("idle"); w.set("thinking"); w.set("idle")
    assert [e["phase"] for e in spy] == ["idle", "thinking", "idle"]


# ---------------------------------------------------------------- the session, Navi's flag
def test_the_session_id_rides_the_record_when_the_caller_knows_it(spy):
    w = L.WorkLive("t-agent", session_id="sid-abc")
    w.set("thinking")
    assert spy[0]["session_id"] == "sid-abc"
    assert spy[0]["session_source"] == "caller"


def test_the_environment_is_the_fallback_not_the_source(spy, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "env-sid")
    w = L.WorkLive("t-agent")
    w.set("thinking")
    assert spy[0]["session_id"] == "env-sid" and spy[0]["session_source"] == "env"


def test_an_unattributable_transition_still_emits_and_says_so(spy, monkeypatch):
    # Zero is not no. Navi's half flagged that liveness has no session in scope; without this the
    # spine would collapse two incarnations of one agent into a single story.
    for v in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
        monkeypatch.delenv(v, raising=False)
    w = L.WorkLive("t-agent")
    w.set("thinking")
    assert spy[0]["session_id"] == "" and spy[0]["session_source"] == "unknown"


# ---------------------------------------------------------------- it must not wedge the beater
def test_the_emit_happens_after_the_lock_is_released(monkeypatch):
    """A phase change must not hold the beater's mutex across a network write. Proven by having the
    emit try to take the same lock: if we were still inside it, this deadlocks and the pin times
    out rather than passing quietly."""
    w = L.WorkLive("t-agent")
    monkeypatch.setattr(L, "_client", lambda: None)
    held = []

    def emit(**kw):
        held.append(w._lock.acquire(blocking=False))
        if held[-1]:
            w._lock.release()

    monkeypatch.setattr(L, "_emit_phase", emit)
    w.set("thinking")
    assert held == [True], "the emit ran while the beater's lock was still held"


def test_a_failing_emit_never_breaks_a_phase_change(monkeypatch):
    def boom(**kw):
        raise RuntimeError("the store is down, which is when this matters most")
    monkeypatch.setattr(L, "_emit_phase", boom)
    monkeypatch.setattr(L, "_client", lambda: None)
    w = L.WorkLive("t-agent")
    w.set("thinking")                              # must not raise
    assert w._phase == "thinking"                  # and must still have done its real job


def test_the_emit_is_not_called_on_the_refresh_thread_under_concurrency(spy):
    """20 heartbeat threads beating while the work path changes phase twice: exactly two records."""
    w = L.WorkLive("t-agent")
    stop = threading.Event()

    def beat():
        while not stop.is_set():
            w.refresh()
            time.sleep(0.001)

    threads = [threading.Thread(target=beat, daemon=True) for _ in range(20)]
    [t.start() for t in threads]
    w.set("thinking"); time.sleep(0.05); w.set("idle")
    stop.set(); [t.join(timeout=2) for t in threads]
    assert [e["phase"] for e in spy] == ["thinking", "idle"]
