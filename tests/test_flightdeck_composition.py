"""flightdeck composition pins — the "composed_of" contract (dsh_agent, 2026-09-21).

Daniel's ask: combo verbs must SHOW what they are a combo of, so stacking verbs never
loses legibility of the fundamentals. These pins make that structural:

  P1  composed_of is DECLARED and matches the sections actually built (membership)
  P2  the recipe names the two new sources: asks (open-ask ledger) + turns
      (the in-flight reasoning signal)
  P3  single-agent mode appends unwedge to the recipe
  P4  asks section composes expectations.snapshot -> open/redriving/overdue counts
  P5  turns section composes turn_metrics.progress_view -> phase + elapsed_s
  P6  format renders the composition as a table of contents

The law being pinned (provenance, one level up — same law as R1 in the eye-fuzzy spec):
a view must say what it is a view over, and the declaration is TESTED against what the
view actually composes. A declared source that is not built, or a built source that is
not declared, fails P1 — the "unwired detector" / derived-artifact-membership lesson,
applied to the tool surface instead of an index.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.doctor import (  # noqa: E402
    FLIGHTDECK_COMPOSITION,
    flightdeck,
    format_flightdeck,
)


@pytest.fixture()
def patched(monkeypatch):
    monkeypatch.setattr("core.comm.doctor.examine_fleet", lambda **kw: {
        "summary": "doctor: 1 page, 0 banner across 2 agent(s)",
        "agents": ["claude", "deepseek"],
        "findings": [
            {"agent": "claude", "state": "stalled_consumer", "grade": "page",
             "line": "claude: STALLED", "drill": "sync"},
            {"agent": "deepseek", "state": "lane_health", "grade": "dashboard",
             "line": "deepseek: lane cursor", "drill": "mailbox"},
        ],
        "pages": [{"agent": "claude", "state": "stalled_consumer", "grade": "page",
                    "line": "STALLED", "drill": "sync"}],
    })
    monkeypatch.setattr("core.comm.doctor.pulse", lambda agents=None: {
        "summary": "pulse: 1 elevated (claude), 1 normal",
        "zones": {"critical": [], "elevated": ["claude"],
                  "normal": ["deepseek"], "absent": []},
        "readings": {"claude": {"backlog": 12, "zone": "elevated", "has_lane": True},
                     "deepseek": {"backlog": 3, "zone": "normal", "has_lane": True}},
    })
    monkeypatch.setattr("core.comm.doctor._probe_lane_health", lambda a: {
        "claude": {"age_s": 1800, "depth": 12, "straggler": 0},
        "deepseek": {"age_s": 120, "depth": 3, "straggler": 0},
    }.get(a))
    monkeypatch.setattr("core.comm.doctor.unwedge", lambda a: {
        "agent": a, "status": "stalled" if a == "claude" else "healthy",
        "verdict": f"{a}: STALLED" if a == "claude" else f"{a}: HEALTHY",
        "recommendation": "sync" if a == "claude" else "none",
        "evidence": {"findings": [
            {"grade": "page", "state": "stalled", "line": "STALLED"} if a == "claude"
            else {"grade": "dashboard", "state": "ok", "line": "ok"}
        ], "runner_status": "live"},
    })

    class _MockLM:
        def __init__(self, agent):
            self._agent = agent

        def list_held(self):
            return ["docs/WISHLIST.md"] if self._agent == "claude" else []

    monkeypatch.setattr("core.comm.locks.LockManager", _MockLM)

    class _R:
        stdout = "abc1234 ship W16\n5678def build pulse\n"
        returncode = 0

    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _R())

    # NEW sources — the composition delta under test.
    # deadline_ts=1.0 is always past (overdue); 9999999999.0 is always future.
    monkeypatch.setattr("core.comm.expectations.snapshot", lambda sender: {
        "claude": {"q1": {"to": "kimi", "attempt": 0,
                          "deadline_ts": 9999999999.0, "created": 1.0}},
        "deepseek": {"q2": {"to": "kimi", "attempt": 2,
                            "deadline_ts": 1.0, "created": 1.0},
                     "q3": {"to": "sol", "attempt": 0,
                            "deadline_ts": 9999999999.0, "created": 1.0}},
    }.get(sender, {}))
    monkeypatch.setattr("core.comm.turn_metrics.progress_view", lambda a: {
        "claude": {"phase": "running", "ask_kind": "question",
                   "elapsed_s": 47.5, "points_seen": 3, "eta": None,
                   "pct_estimate": None},
        "deepseek": None,   # idle — honest absence, never a fabricated turn
    }.get(a))


def test_p1_composed_of_declared_and_matches_built(patched):
    fd = flightdeck()
    assert "composed_of" in fd, "the cockpit must carry its own table of contents"
    assert set(fd["composed_of"]) == set(fd["sections"].keys()), (
        "declaration == reality: a declared source that is not built, or a built source "
        "that is not declared, is the drift this contract exists to catch")
    assert list(fd["composed_of"]) == list(FLIGHTDECK_COMPOSITION), (
        "fleet mode composes exactly the declared base recipe, in order")


def test_p2_recipe_names_asks_and_turns(patched):
    fd = flightdeck()
    assert "asks" in fd["composed_of"] and "turns" in fd["composed_of"]
    assert "asks" in fd["sections"] and "turns" in fd["sections"]


def test_p3_single_agent_appends_unwedge(patched):
    fd = flightdeck(agent="claude")
    assert "unwedge" in fd["composed_of"]
    assert set(fd["composed_of"]) == set(fd["sections"].keys())
    assert len(fd["composed_of"]) == len(FLIGHTDECK_COMPOSITION) + 1


def test_p4_asks_composes_open_ledger(patched):
    fd = flightdeck()
    asks = fd["sections"]["asks"]
    assert asks["claude"]["n_open"] == 1
    assert asks["claude"]["n_redriving"] == 0
    assert asks["claude"]["n_overdue"] == 0
    assert asks["deepseek"]["n_open"] == 2
    assert asks["deepseek"]["n_redriving"] == 1, "attempt>0 reads as redriving"
    assert asks["deepseek"]["n_overdue"] == 1, "deadline already past reads as overdue"


def test_p5_turns_composes_inflight_signal(patched):
    fd = flightdeck()
    turns = fd["sections"]["turns"]
    assert turns["claude"]["phase"] == "running"
    assert turns["claude"]["elapsed_s"] == 47.5
    assert turns["deepseek"] is None, "idle is honest absence, not a fabricated turn"


def test_p6_format_renders_composition_toc(patched):
    out = format_flightdeck(flightdeck())
    low = out.lower()
    assert "composed_of" in low, "the text render leads with the composition"
    assert "open asks" in low, "the asks section is rendered with its source named"
    assert "in-flight" in low, "the turns section is rendered with its source named"


def test_p7_last_turn_composes(patched, monkeypatch):
    monkeypatch.setattr("core.comm.doctor._last_turn", lambda a: {
        "deepseek": {"ask_kind": "nudge", "duration_s": 39.5, "age_s": 120.0},
        "claude": None,
    }.get(a))
    fd = flightdeck()
    assert "last_turn" in fd["composed_of"], (
        "the recipe names the last-turn source -- 'what did they just do'")
    lt = fd["sections"]["last_turn"]
    assert lt["deepseek"]["ask_kind"] == "nudge"
    assert lt["deepseek"]["duration_s"] == 39.5
    assert lt["deepseek"]["age_s"] == 120.0
    assert lt["claude"] is None, "no turn history is an honest absence, not a zero"


def test_p8_render_shows_last_turn(patched, monkeypatch):
    monkeypatch.setattr("core.comm.doctor._last_turn", lambda a: {
        "deepseek": {"ask_kind": "nudge", "duration_s": 39.5, "age_s": 120.0},
    }.get(a))
    out = format_flightdeck(flightdeck())
    low = out.lower()
    assert "last turn" in low, "the last-turn section is rendered with its source named"
    assert "nudge" in low and "39.5s" in low


def test_p9_last_turn_reads_firehose_most_recent():
    from core.comm.doctor import _last_turn

    class _Log:
        def __init__(self, rows):
            self._rows = rows

        def scan(self, agent):
            return self._rows

    r = _last_turn("deepseek", now=1000.0, log=_Log([
        {"kind": "turn_metrics", "detail": {"ts": 900.0, "ask_kind": "question",
                                            "duration_s": 60.0}},
        {"kind": "turn_metrics", "detail": {"ts": 950.0, "ask_kind": "nudge",
                                            "duration_s": 39.5}},
        {"kind": "boot", "detail": {}},
        {"kind": "turn_metrics", "detail": {"ask_kind": "no_ts", "duration_s": 1.0}},
    ]))
    assert r == {"ask_kind": "nudge", "duration_s": 39.5, "age_s": 50.0}, (
        "the most recent turn_metrics wins; a missing ts is skipped, never guessed")
    assert _last_turn("x", now=1000.0, log=_Log([])) is None
    assert _last_turn("x", now=1000.0, log=_Log([
        {"kind": "not_a_turn", "detail": {"ts": 950.0}},
    ])) is None
