"""PRE-REGISTERED ACCEPTANCE -- escalation on PROGRESS AGE (handoff item B).

The receipt this is written from (2026-07-26): kimi's work lane sat undrained for
45 HOURS. The doctor COMPUTED it -- cursor age 164119s, depth 55 -- and filed it
DASHBOARD-grade, beside routine token spend. Detection existed; SEVERITY was wrong,
and the finding rode a channel nobody acts on. Same shape as the door arc: a
computed red routed nowhere is not a guard.

Two independent holes, two halves of this file:

  GRADING (P1-P5). W16's lane_health row is unconditionally 'dashboard' however old
  it gets. The kimi shape is specifically one a FRESH PULSE hides: the seat was alive
  and looping, so `working` rendered "genuinely working, not wedged" -- true of the
  PROCESS, false of the WORK. Progress age must page independently of the pulse.
  The signal is BACKLOG age (oldest unconsumed entry), never raw cursor age: a quiet
  agent with no mail has an ancient cursor and is perfectly healthy (P3/P4 are the
  false-positive guards that separate the two).

  ROUTING (P6-P8). core/comm/pager.py is the ONLY channel that reaches a human (the
  UserPromptSubmit hook injects [PAGE] lines into any live seat). Its sole writer is
  the daemon's runner-down check. The doctor -- which OWNS the paging table -- has
  never written to it. A page that reaches only a bus note repeats the original sin.

Run: py -m pytest tests/test_lane_stall_escalation.py -q
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _thresholds():
    """Read from the module so the pins hold under any timescale scaling."""
    from core.comm import doctor
    return (float(getattr(doctor, "LANE_STALL_PAGE_S", 6 * 3600)),
            float(getattr(doctor, "LANE_STALL_WARN_S", 3600)))


def _probes(**over):
    """A healthy-idle agent by default; each test overrides one facet."""
    base = dict(
        worklive=lambda a: {"phase": "idle", "detail": "", "turn": 3,
                            "since_ts": time.time() - 5, "beat_ts": time.time() - 1},
        progress=lambda a: None,
        backlog=lambda a: 0,
        stalled_since=lambda a, present: None,
        halted=lambda a: None,
        lane_health=lambda a: None,
        now=time.time(),
    )
    base.update(over)
    return base


def _lane(depth=0, backlog_age_s=None, age_s=None, straggler=0):
    return {"age_s": age_s, "depth": depth, "straggler": straggler,
            "backlog_age_s": backlog_age_s}


# ---------------------------------------------------------------- GRADING (P1-P5)
def test_p1_aged_backlog_pages():
    """Undrained work past the page threshold is page-grade, with a drill-down."""
    from core.comm.doctor import examine
    page_s, _ = _thresholds()
    f = examine("kimi", probes=_probes(
        lane_health=lambda a: _lane(depth=55, backlog_age_s=page_s + 600,
                                    age_s=page_s + 600)))
    stall = next((x for x in f if x["state"] == "lane_stall"), None)
    assert stall is not None, "an aged, undrained work lane must produce a lane_stall finding"
    assert stall["grade"] == "page", "45h of undrained work is not a dashboard row"
    assert stall["drill"], "every finding carries its drill-down"


def test_p2_a_fresh_pulse_does_not_silence_the_stall():
    """THE KIMI REGRESSION. Alive, looping, pulse fresh, non-idle phase -- and the
    work lane has not moved in 45h. The pulse proves the PROCESS; it must not be
    allowed to speak for the WORK."""
    from core.comm.doctor import examine
    page_s, _ = _thresholds()
    now = time.time()
    f = examine("kimi", probes=_probes(
        worklive=lambda a: {"phase": "handling", "detail": "long review", "turn": 900,
                            "since_ts": now - 400, "beat_ts": now - 1},
        progress=lambda a: {"age_s": 1.5, "generation": 4, "detail": "tool:read_file"},
        lane_health=lambda a: _lane(depth=55, backlog_age_s=page_s + 600,
                                    age_s=page_s + 600),
        now=now))
    assert any(x["state"] == "working" for x in f), "the fresh-pulse row still renders"
    stall = next((x for x in f if x["state"] == "lane_stall"), None)
    assert stall is not None and stall["grade"] == "page", (
        "a fresh pulse must NOT silence progress age -- this is exactly how 45h passed")


def test_p3_quiet_lane_never_pages():
    """FALSE-POSITIVE GUARD. No mail for days: the cursor is ancient because nothing
    arrived, not because anyone stalled. Zero depth = zero pages, at any age."""
    from core.comm.doctor import examine
    page_s, _ = _thresholds()
    f = examine("sol", probes=_probes(
        lane_health=lambda a: _lane(depth=0, backlog_age_s=None,
                                    age_s=page_s * 10)))
    assert not any(x["grade"] == "page" for x in f), (
        "an ancient cursor with an EMPTY backlog is a quiet agent, not a stalled one")


def test_p4_fresh_work_on_an_ancient_cursor_never_pages():
    """THE DISCRIMINATOR. Cursor age is ancient (last consumed days ago) but the work
    that is waiting arrived a minute ago. Grading on cursor age -- the obvious reading
    of 'if lane_cursor_age > 6h' -- pages here, and would page every returning seat."""
    from core.comm.doctor import examine
    page_s, _ = _thresholds()
    f = examine("deepseek", probes=_probes(
        lane_health=lambda a: _lane(depth=3, backlog_age_s=60,
                                    age_s=page_s * 5)))
    assert not any(x["grade"] == "page" for x in f), (
        "the signal is how long WORK has waited, never how old the cursor timestamp is")


def test_p5_warn_band_is_visible_before_it_pages():
    """Between warn and page: on the dashboard, not yet a page -- the same shape as
    approaching_wedge, so no mission face can render this window as 'healthy'."""
    from core.comm.doctor import examine
    page_s, warn_s = _thresholds()
    mid = (warn_s + page_s) / 2.0
    f = examine("deepseek", probes=_probes(
        lane_health=lambda a: _lane(depth=4, backlog_age_s=mid, age_s=mid)))
    stall = next((x for x in f if x["state"] == "lane_stall"), None)
    assert stall is not None, "the warn band is visible"
    assert stall["grade"] == "dashboard", "it observes before it pages"


# ---------------------------------------------------------------- ROUTING (P6-P8)
class FakeRedis:
    """Enough Redis for the dedup key + the pager list."""
    def __init__(self):
        self.kv = {}
        self.lists = {}
    def set(self, k, v, nx=False, ex=None):
        if nx and k in self.kv:
            return None
        self.kv[k] = v
        return True
    def get(self, k):
        return self.kv.get(k)
    def delete(self, k):
        self.kv.pop(k, None)
        self.lists.pop(k, None)
    def lpush(self, k, v):
        self.lists.setdefault(k, []).insert(0, v)
        return len(self.lists[k])
    def ltrim(self, k, a, b):
        self.lists[k] = self.lists.get(k, [])[a:b + 1]
    def lrange(self, k, a, b):
        L = self.lists.get(k, [])
        return L[a:] if b == -1 else L[a:b + 1]


@pytest.fixture()
def fake(monkeypatch):
    c = FakeRedis()
    monkeypatch.setenv("BIFROST_NAMESPACE", "t-lane-stall")
    monkeypatch.setattr("core.comm.doctor._client", lambda: c)
    return c


def _page_finding():
    return {"agent": "kimi", "state": "lane_stall", "grade": "page",
            "line": "kimi: LANE STALL -- 55 undrained for 164119s", "drill": "py agent_cli.py unwedge kimi"}


def test_p6_page_grade_reaches_the_pager(fake):
    """The whole point of item B: a page must land where a HUMAN sees it."""
    from core.comm import doctor, pager
    doctor._emit_pages([_page_finding()])
    items = pager.unread_pages(c=fake)
    assert items, "a page-grade finding must reach the pager (the only human-facing channel)"
    assert any("kimi" in str(i.get("agent", "")) or "kimi" in str(i.get("text", ""))
               for i in items), "the paged agent is identifiable in the pager entry"


def test_p7_escalation_dedups_within_the_window(fake):
    """A stall re-observed every boot must not flood the capped pager list."""
    from core.comm import doctor, pager
    for _ in range(5):
        doctor._emit_pages([_page_finding()])
    assert len(pager.unread_pages(c=fake)) == 1, (
        "one escalation per (agent, state) per dedup window")


def test_p9_the_synthesizer_may_never_contradict_its_own_page(monkeypatch):
    """unwedge() is the drill-down every page points at. Its ladder tested depth + a
    fresh pulse and returned 'BUSY -- working, not wedged' while PRINTING the
    page-grade lane_stall directly beneath it -- the same reasoning that let kimi's
    45h pass, one level up, in the tool sent to investigate it. The invariant is
    general: a verdict must never read healthy while a page sits in its evidence."""
    from core.comm import doctor
    page_s, _ = _thresholds()
    monkeypatch.setattr(doctor, "examine", lambda a, **k: [_page_finding()])
    monkeypatch.setattr(doctor, "_probe_lane_health",
                        lambda a: _lane(depth=22, backlog_age_s=page_s * 4,
                                        age_s=page_s * 4))
    # Reproduce the LIVE condition exactly: a healthy runner is what routed the real
    # verdict into the 'BUSY -- working, not wedged' branch.
    monkeypatch.setattr("core.comm.runner_lock.holder", lambda a: {"token": "t"})
    monkeypatch.setattr("core.comm.incarnation.daemon_runtimes", lambda a: {})
    r = doctor.unwedge("kimi")
    assert r["status"] not in ("healthy", "backlogged"), (
        f"a page-grade finding forbids a healthy verdict (got {r['status']})")
    assert "not wedged" not in r["verdict"].lower(), (
        "the drill-down must not talk the reader out of the page it was sent to explain")


def test_p10_the_stall_verdict_is_actionable(monkeypatch):
    """It names what is wrong (how long work waited) and what to do about it."""
    from core.comm import doctor
    page_s, _ = _thresholds()
    monkeypatch.setattr(doctor, "examine", lambda a, **k: [_page_finding()])
    monkeypatch.setattr(doctor, "_probe_lane_health",
                        lambda a: _lane(depth=22, backlog_age_s=page_s * 4,
                                        age_s=page_s * 4))
    # Reproduce the LIVE condition exactly: a healthy runner is what routed the real
    # verdict into the 'BUSY -- working, not wedged' branch.
    monkeypatch.setattr("core.comm.runner_lock.holder", lambda a: {"token": "t"})
    monkeypatch.setattr("core.comm.incarnation.daemon_runtimes", lambda a: {})
    r = doctor.unwedge("kimi")
    assert "stall" in r["verdict"].lower()
    assert r["recommendation"], "a page-grade verdict always carries a next action"


def test_p8_escalation_survives_a_dead_bus(monkeypatch, fake):
    """FAIL-OPEN, AND THE ORDERING THAT MATTERS: when the bus cannot be constructed,
    the human-facing escalation must still fire. A bus outage is exactly when a stall
    is most likely and least visible."""
    from core.comm import doctor, pager

    class DeadBus:
        def __init__(self, *a, **k):
            raise RuntimeError("bus down")

    monkeypatch.setattr("core.comm.bus.Bus", DeadBus)
    doctor._emit_pages([_page_finding()])          # must not raise
    assert pager.unread_pages(c=fake), (
        "the pager write must not sit behind a Bus construction that can fail")
