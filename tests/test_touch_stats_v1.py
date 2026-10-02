"""W0.4 pins (RED first): the instrument -- what the touch stream actually costs and covers.

SPEC: W0.4 of `fences/context-system/reconciliation.md` section 4 -- "touches per hour by seat,
      commands per touch, refs per touch, p95 hook latency, ring retention_ms, drop counter, and
      the L1 cost of the receipt anchor; run for 24 h before Wave 1". Heimdall reads the 24 h
      number and rules A5b (shared firehose or its own ring).

WHY THIS IS BUILT TONIGHT RATHER THAN TOMORROW: it is the only slice in Wave 0 that is TIME-GATED.
It has to run for 24 h before Wave 1 fences, so the clock starts when the verb exists, not when
someone remembers it.

THE NUMBER THIS EXISTS TO MOVE. Measured on `events:raw` before W0.2 shipped: 89 of 6,918 records
carried a session id, all of one kind, and no kind the hook emits carried one. That is the reach
map's "0.0% of captured events carrying a session id". Session coverage is therefore the headline
statistic, because it is the one the whole wave is for, and a wave that cannot show its own number
moving is a wave nobody can audit.

WHAT IS DELIBERATELY REPORTED AS UNCHECKABLE RATHER THAN ESTIMATED. The spec asks for p95 hook
latency and the L1 cost of the receipt anchor. Neither is captured today -- the PostToolUse payload
carries no duration, and `touch.v1` does not yet stamp one. An instrument that INVENTS a number it
cannot measure is worse than one that admits the hole, because the invented number gets quoted.
These come back as UNCHECKABLE with the reason attached, which is this house's own "zero is not no"
law applied to its own instrument, and it names the next slice instead of hiding it.

Hermetic: every statistic is computed from a list of records handed in. Nothing reads Redis.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.events import touch_stats as S  # noqa: E402

HOUR = 3600.0
T0 = 1_790_900_000.0


def rec(kind="touch", *, at=T0, agent="claude", session="sid-1", targets=2,
        incomplete=False, total=None, truncated=False):
    d = {"at": at, "kind": kind, "agent_id": agent, "session_id": session, "detail": {}}
    if kind == "touch":
        d["detail"] = {
            "schema": "touch.v1", "tool": "Bash",
            "targets": None if targets is None else [{"action": "read", "key": f"f{i}.py"}
                                                     for i in range(targets)],
            "targets_total": total if total is not None else (targets or 0),
            "targets_truncated": truncated,
            "targets_incomplete": incomplete,
            "session_source": "payload" if session else "unknown",
        }
    return d


# ---------------------------------------------------------------- coverage, the headline
def test_session_coverage_is_the_headline_statistic():
    r = S.compute([rec(session="a"), rec(session="b"), rec(session="")], now=T0 + 60)
    assert r["session_coverage"]["with_session"] == 2
    assert r["session_coverage"]["total"] == 3
    assert abs(r["session_coverage"]["share"] - (2 / 3)) < 1e-9


def test_coverage_is_reported_across_every_kind_not_only_touches():
    # The wave's claim is about the SPINE, so measuring only our own kind would grade our homework.
    r = S.compute([rec(), rec(kind="fail", session=""), rec(kind="boot", session="")], now=T0 + 60)
    assert r["session_coverage"]["total"] == 3
    assert r["session_coverage"]["by_kind"]["fail"]["with_session"] == 0
    assert r["session_coverage"]["by_kind"]["touch"]["with_session"] == 1


def test_an_empty_stream_reports_a_measured_zero_not_a_crash():
    r = S.compute([], now=T0)
    assert r["session_coverage"]["total"] == 0
    assert r["session_coverage"]["share"] is None     # a share of nothing is not 0.0, it is unknown


# ---------------------------------------------------------------- rate and shape
def test_touches_per_hour_by_seat():
    recs = [rec(at=T0 + i * 60, agent="claude") for i in range(30)] + \
           [rec(at=T0 + i * 60, agent="kimi") for i in range(10)]
    r = S.compute(recs, now=T0 + HOUR)
    assert r["touches_per_hour"]["claude"] == pytest.approx(30.0, rel=0.01)
    assert r["touches_per_hour"]["kimi"] == pytest.approx(10.0, rel=0.01)


def test_targets_per_touch_reports_a_distribution_not_only_a_mean():
    # A mean alone hides the shape, and the shape is what decides the cap and the ring size.
    r = S.compute([rec(targets=n) for n in (0, 1, 1, 2, 40)], now=T0 + 60)
    t = r["targets_per_touch"]
    assert t["mean"] == pytest.approx(8.8)
    assert t["p50"] == 1 and t["max"] == 40


def test_the_share_of_commands_we_could_not_see_into_is_reported():
    r = S.compute([rec(targets=None, incomplete=True), rec(), rec(), rec()], now=T0 + 60)
    assert r["incomplete_share"] == pytest.approx(0.25)


def test_the_truncation_share_is_reported_so_the_cap_can_be_judged():
    r = S.compute([rec(targets=32, total=90, truncated=True), rec()], now=T0 + 60)
    assert r["truncated_share"] == pytest.approx(0.5)


# ---------------------------------------------------------------- the ring, and the drops
def test_ring_retention_is_measured_from_the_oldest_record_not_assumed():
    r = S.compute([rec(at=T0), rec(at=T0 + 6 * HOUR)], now=T0 + 6 * HOUR)
    assert r["ring_retention_h"] == pytest.approx(6.0, rel=0.01)


def test_the_drop_counter_rides_the_report():
    r = S.compute([rec()], now=T0 + 60, drops=7)
    assert r["drops"] == 7


def test_a_horizon_shorter_than_the_window_is_flagged_because_the_ring_is_eating_history():
    # If the oldest record is younger than the window asked for, the ring has already dropped
    # records inside it, and every rate computed over that window is understated.
    r = S.compute([rec(at=T0 + 23 * HOUR)], now=T0 + 24 * HOUR, window_h=24)
    assert r["window_truncated_by_ring"] is True


# ---------------------------------------------------------------- honest holes
def test_what_is_not_measured_is_named_uncheckable_never_estimated():
    r = S.compute([rec()], now=T0 + 60)
    for field in ("p95_hook_latency_ms", "anchor_resolve_cost_ms"):
        assert r[field] == S.UNCHECKABLE
    assert "duration" in r["uncheckable_why"]["p95_hook_latency_ms"].lower()


def test_uncheckable_is_distinct_from_zero_everywhere_it_appears():
    r = S.compute([], now=T0)
    assert r["p95_hook_latency_ms"] is not 0 and r["p95_hook_latency_ms"] == S.UNCHECKABLE


# ---------------------------------------------------------------- the window
def test_records_outside_the_window_are_excluded_from_rates():
    old = [rec(at=T0 - 48 * HOUR) for _ in range(100)]
    new = [rec(at=T0 + i * 60) for i in range(5)]
    r = S.compute(old + new, now=T0 + HOUR, window_h=24)
    assert r["session_coverage"]["total"] == 5, "the window must bound the whole report, not some of it"


def test_the_report_states_the_window_it_used():
    r = S.compute([rec()], now=T0 + 60, window_h=24)
    assert r["window_h"] == 24
