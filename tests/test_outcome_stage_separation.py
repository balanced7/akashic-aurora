"""Stage separation + the prevention numerator (2026-07-25, from the four-seat debate).

THE DEFECT. `_log_flip` fused OUTCOME and ATTRIBUTION into one record, and wrote it ONLY
when a FAIL->SUCCESS flip occurred. A first-try success wrote nothing at all -- the
contrastive gate was explicit in the source: "a first-try success credits and logs nothing."

So the only value metric counted RESCUE and never PREVENTION. The single most valuable
thing a lesson can do -- stop the failure happening -- was invisible. kimi found it by
reading the mechanism; codex showed the complementary half (C/N divides a terminal signal
by corpus production across five unmeasured stages, so four credits localises nothing).
Both corrections landed on one build: make the stages distinct events.

  S1  first-try SUCCESS with a lesson surfaced -> an outcome event (logged NOTHING before)
  S2  first-try SUCCESS with NO lesson surfaced -> an event too (the control arm)
  S3  a real FAIL->SUCCESS flip still flips, still credits, still logs the flip (no regression)
  S4  prevention_rate computes the contrast and the lift
  S5  only the FIRST resolution per target counts (first-try semantics, not eventual)
  S6  the outcome stage is OBSERVATION ONLY -- it must not move any ranking counter
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall import at_action


def _sid():
    return "stagetest-" + uuid.uuid4().hex[:10]


def test_s1_first_try_success_with_lesson_is_recorded():
    """The prevention case. Before this slice it produced no record of any kind."""
    sid, tgt = _sid(), at_action.normalize_target(command="echo prevention")
    at_action.mark_impression(sid, tgt, ["learn:experiment:some_lesson"])
    res = at_action.resolve_action_outcome(sid, tgt, True)
    assert res["flipped"] is False, "first-try success is not a flip"
    assert res["credited"] == 0, "and it must still credit nothing (contrastive gate intact)"

    recs = at_action.session_outcomes(sid)
    assert len(recs) == 1, "but it MUST now leave an outcome record"
    assert recs[0]["ok"] is True
    assert recs[0]["surfaced"] is True, "the surfaced flag is what makes prevention visible"
    assert recs[0]["flipped"] is False


def test_s2_first_try_success_without_lesson_is_the_control_arm():
    sid, tgt = _sid(), at_action.normalize_target(command="echo control")
    at_action.resolve_action_outcome(sid, tgt, True)
    recs = at_action.session_outcomes(sid)
    assert len(recs) == 1
    assert recs[0]["ok"] is True and recs[0]["surfaced"] is False


def test_s3_real_flip_still_flips_and_logs(monkeypatch):
    """No regression: the rescue path must behave exactly as before."""
    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid, tgt = _sid(), at_action.normalize_target(command="echo rescue")
    at_action.mark_impression(sid, tgt, ["learn:experiment:rescuer"])
    at_action.resolve_action_outcome(sid, tgt, False)          # FAIL
    res = at_action.resolve_action_outcome(sid, tgt, True)     # ...then SUCCESS
    assert res["flipped"] is True, "the flip path is unchanged"
    assert res["credited"] == 1
    assert at_action.session_flips(sid), "the flip log still receives it"
    recs = at_action.session_outcomes(sid)
    assert len(recs) == 2, "and BOTH resolutions are now staged"
    assert recs[0]["ok"] is False and recs[1]["flipped"] is True


def test_s4_prevention_rate_contrasts_the_two_arms():
    sid = _sid()
    for i in range(3):                                    # surfaced arm: 3 tries, 2 succeed
        t = at_action.normalize_target(command=f"echo w{i}")
        at_action.mark_impression(sid, t, ["learn:experiment:l"])
        at_action.resolve_action_outcome(sid, t, i < 2)
    for i in range(2):                                    # control arm: 2 tries, 0 succeed
        t = at_action.normalize_target(command=f"echo o{i}")
        at_action.resolve_action_outcome(sid, t, False)

    pr = at_action.prevention_rate(sid)
    assert pr["with_lesson"]["n"] == 3 and pr["with_lesson"]["ok"] == 2
    assert pr["without_lesson"]["n"] == 2 and pr["without_lesson"]["ok"] == 0
    assert pr["rate_with"] == pytest.approx(2 / 3)
    assert pr["rate_without"] == 0.0
    assert pr["lift"] == pytest.approx(0.6667, abs=1e-3)


def test_s5_only_the_first_resolution_per_target_counts():
    """FIRST-try semantics. A target that fails then succeeds must count as a FAILURE for
    prevention purposes -- otherwise every eventual success inflates the rate."""
    sid, tgt = _sid(), at_action.normalize_target(command="echo eventual")
    at_action.mark_impression(sid, tgt, ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, tgt, False)
    at_action.resolve_action_outcome(sid, tgt, True)
    pr = at_action.prevention_rate(sid)
    assert pr["with_lesson"]["n"] == 1, "one target, one first-try observation"
    assert pr["with_lesson"]["ok"] == 0, "the FIRST try failed; the later rescue is not prevention"


def test_s7_contrast_counts_per_session_and_target():
    """The durable reader spans sessions, so the first-try key must be (session, target) --
    otherwise one session's target silently suppresses every other session's observation
    of the same file, and the fleet-wide rate reads from a fraction of the evidence. That
    is the starved-index genus wearing a different hat."""
    recs = [
        {"sid": "a", "t": "p:/x", "ok": True, "surfaced": True},
        {"sid": "a", "t": "p:/x", "ok": False, "surfaced": True},   # same pair -> ignored
        {"sid": "b", "t": "p:/x", "ok": False, "surfaced": True},   # different session -> counts
        {"sid": "b", "t": "p:/y", "ok": True, "surfaced": False},
    ]
    c = at_action._contrast(recs)
    assert c["with_lesson"] == {"n": 2, "ok": 1}, "one per (session,target), not one per target"
    assert c["without_lesson"] == {"n": 1, "ok": 1}


def test_s9_tests_never_write_the_canonical_durable_stream(monkeypatch):
    """THE ONE I BROKE. The first durable mirror wrote test fixtures into the canonical
    stream: 36 of its first 51 records were these very pins. conftest redirects the tempdir
    (AKASHIC_RECALL_STATE_DIR) but nothing redirects the event log, so the two writers had
    different isolation and only one was honest about it. Same genus as the suite replacing
    the live learning index -- committed by the seat that had filed that lesson hours
    earlier. This pin makes the regression impossible to reintroduce silently."""
    emitted = []
    import core.events.event_log as el

    class _FakeLedger:
        def emit(self, *a, **k):
            emitted.append(a)

    monkeypatch.setattr(el, "get_event_log",
                        lambda: type("L", (), {"ledger": _FakeLedger()})())
    monkeypatch.setenv("AKASHIC_RECALL_STATE_DIR", "/tmp/redirected")
    sid, tgt = _sid(), at_action.normalize_target(command="echo isolation")
    at_action.resolve_action_outcome(sid, tgt, True)
    assert emitted == [], "a redirected state root must never reach the canonical stream"
    assert at_action.session_outcomes(sid), "the local record is still written"


def test_s8_durable_readers_are_fail_soft(monkeypatch):
    """A PostToolUse-adjacent reader must never raise when the store is down."""
    import core.events.event_log as el

    def boom():
        raise RuntimeError("store down")

    monkeypatch.setattr(el, "get_event_log", boom)
    assert at_action.durable_outcomes(30) == []
    pr = at_action.prevention_rate_durable(30)
    assert pr["lift"] is None and pr["with_lesson"]["n"] == 0


def test_s6_outcome_stage_does_not_steer_ranking(monkeypatch):
    """The debate's unanimous constraint: no automatic feedback, positive or negative,
    until the stages are separately observed. Recording an outcome must touch NO counter."""
    calls = []
    monkeypatch.setattr(at_action, "record_feedback",
                        lambda *a, **k: calls.append(a) or True)
    monkeypatch.setattr(at_action, "bump_surfaced",
                        lambda *a, **k: calls.append(("bump",) + a))
    sid, tgt = _sid(), at_action.normalize_target(command="echo nosteer")
    at_action.mark_impression(sid, tgt, ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, tgt, True)      # first-try success
    assert calls == [], "a non-flip outcome must move no ranking counter at all"
    assert at_action.session_outcomes(sid), "yet it is still observed"
