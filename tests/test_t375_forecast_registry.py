"""
T375 -- engineering forecast registry: pins, RED-first per M3.

Bar (pre-registered BEFORE implementation; provenance: Heimdall's trader
counter SQ5 -- "an append-only forecast_registry + a harness gate 'no atom
with knowable-ts > registered-at enters a backtest'" -- generalized to
engineering bets; Daniil's B-C-D-A ruling; dies_when from the hope riff):

  P1  APPEND-ONLY: registering a duplicate id is refused; there is no edit
      door -- correction = a new register + voiding score, never mutation.
      The on-disk log only ever grows (byte-prefix invariant).
  P2  KNOWABLE-TS: scoring with outcome_knowable_ts earlier than the
      forecast's registered_at is REFUSED (a hindsight bet is named, not
      scored). Scoring without an evidence_ref is refused (no bare claims).
  P3  ECHO-BAN: evidence_ref pointing at the register plane (another
      forecast) is refused -- credit only from OUTCOME joins, never
      agreement. A valid outcome-plane ref scores cleanly.
  P4  CALIBRATION FOLD: hit-rate by author correct on a fixture; a forecast
      past its horizon with no score surfaces as OVERDUE, and scored ones
      never do.

File-backed in a throwaway directory -- no Redis needed; the registry is
git-durable state (state/coord/forecasts.jsonl in production).
Run: py -m pytest tests/test_t375_forecast_registry.py -q
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord.forecast_registry import (  # RED: module does not exist yet
    ForecastRegistry, RegistryRefusal)


NOW = time.time()


def _reg(tmp_path):
    return ForecastRegistry(path=str(tmp_path / "forecasts.jsonl"))


def _register(r, fid="F001", by="claude", registered_at=None, horizon=None):
    return r.register(
        id=fid, task_ref="T999", registered_by=by,
        registered_at=registered_at if registered_at is not None else NOW,
        expectation={"statement": "the suite stays green", "metric": "failures",
                     "target": 0},
        horizon_ts=horizon if horizon is not None else NOW + 3600,
        mechanism="pins gate the door",
        dies_when="the suite is retired")


# ------------------------------------------------------------------ P1 append-only
def test_p1_duplicate_id_refused_and_log_only_grows(tmp_path):
    r = _reg(tmp_path)
    _register(r)
    size_after_first = os.path.getsize(r.path)
    with pytest.raises(RegistryRefusal):
        _register(r)                       # same id again -> refuse, no rewrite
    assert os.path.getsize(r.path) == size_after_first
    with open(r.path, "rb") as f:
        first = f.read()
    _register(r, fid="F002")
    with open(r.path, "rb") as f:
        grown = f.read()
    assert grown.startswith(first), "append-only: the log may only ever grow"
    assert not hasattr(r, "edit"), "no edit door exists by design"


# ------------------------------------------------------------------ P2 knowable-ts
def test_p2_hindsight_bet_refused_and_evidence_required(tmp_path):
    r = _reg(tmp_path)
    _register(r, registered_at=NOW)
    with pytest.raises(RegistryRefusal) as exc:
        r.score("F001", scored_by="claude", scored_at=NOW + 10,
                outcome={"observed": "green", "evidence_ref": "commit:abc123"},
                outcome_knowable_ts=NOW - 60,
                verdict="hit")
    assert "hindsight" in str(exc.value).lower()
    with pytest.raises(RegistryRefusal):
        r.score("F001", scored_by="claude", scored_at=NOW + 10,
                outcome={"observed": "green", "evidence_ref": ""},
                outcome_knowable_ts=NOW + 5, verdict="hit")


# ------------------------------------------------------------------ P3 echo-ban
def test_p3_agreement_is_not_evidence(tmp_path):
    r = _reg(tmp_path)
    _register(r)
    _register(r, fid="F002")
    with pytest.raises(RegistryRefusal) as exc:
        r.score("F001", scored_by="claude", scored_at=NOW + 10,
                outcome={"observed": "F002 predicts the same",
                         "evidence_ref": "forecast:F002"},
                outcome_knowable_ts=NOW + 5, verdict="hit")
    assert "echo" in str(exc.value).lower() or "agreement" in str(exc.value).lower()
    r.score("F001", scored_by="claude", scored_at=NOW + 10,
            outcome={"observed": "suite green at HEAD",
                     "evidence_ref": "commit:abc123"},
            outcome_knowable_ts=NOW + 5, verdict="hit")
    assert r.state()["F001"]["verdict"] == "hit"


# ------------------------------------------------------------------ P4 calibration
def test_p4_calibration_fold_and_overdue(tmp_path):
    r = _reg(tmp_path)
    _register(r, fid="F001", by="claude", registered_at=NOW - 100)
    _register(r, fid="F002", by="claude", registered_at=NOW - 100)
    _register(r, fid="F003", by="deepseek", registered_at=NOW - 100,
              horizon=NOW - 10)             # past horizon, never scored
    r.score("F001", scored_by="claude", scored_at=NOW,
            outcome={"observed": "green", "evidence_ref": "commit:aaa"},
            outcome_knowable_ts=NOW - 5, verdict="hit")
    r.score("F002", scored_by="claude", scored_at=NOW,
            outcome={"observed": "red", "evidence_ref": "commit:bbb"},
            outcome_knowable_ts=NOW - 5, verdict="miss")
    cal = r.calibration()
    assert cal["by_author"]["claude"]["hit"] == 1
    assert cal["by_author"]["claude"]["miss"] == 1
    assert cal["by_author"]["claude"]["rate"] == pytest.approx(0.5)
    overdue = [f["id"] for f in cal["overdue"]]
    assert overdue == ["F003"], "past-horizon unscored forecasts must surface"
