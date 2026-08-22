"""
T375 -- engineering forecast registry: pins, RED-first per M3.

AMENDED after Heimdall's fence counter (bus 1787420737264-0) -- the reconciled
contract, sharper than the freeze in four places:

  P1  APPEND-ONLY + PURE FOLD: duplicate ids refused, no edit door, the log
      only grows -- and registry state is a PURE fold(events) -> dict (the
      seam that makes append-only auditable and a future index a drop-in,
      never a rewrite). The fold must not mutate its input.
  P2  DERIVED KNOWABLE-TS, STRICTLY AFTER: the score door RESOLVES the
      evidence_ref artifact to its own timestamp -- it structurally cannot
      accept a scorer-supplied knowable-ts (a self-stamped timestamp is a
      forged attribution in waiting). Hindsight guard is STRICT: resolved ts
      must be > registered_at; the == boundary refuses (the millisecond seam
      is exactly where hindsight would live). registered_at is likewise
      stamped by the door's clock, never caller-supplied. Missing or
      unresolvable evidence refuses.
  P3  ECHO-BAN + THE ONE CARVE-OUT: evidence pointing at the register plane
      (forecast:...) is agreement, not evidence -- refused for every verdict
      EXCEPT voided, the only verdict that is a statement about the bet
      rather than a claim about the world. voided is the sole no-artifact
      path, or it becomes the hindsight escape hatch.
  P4  CALIBRATION FOLD + ENUM: hit-rate by author; past-horizon unscored
      forecasts surface as OVERDUE; the verdict enum carries the documented
      trader-inheritance member `residual` (directionally right, no alpha)
      even though this instance never uses it -- the enum is the primitive,
      this organ uses a subset.

File-backed in a throwaway directory; evidence refs in fixtures use the
event:<stream>:<ms>-<seq> scheme (self-timestamping, no Redis needed).
Run: py -m pytest tests/test_t375_forecast_registry.py -q
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord.forecast_registry import (  # noqa: E402
    ForecastRegistry, RegistryRefusal, VERDICTS, fold)


T0 = 1_700_000_000.0                 # fixture epoch, seconds


def _ev_ref(ts_s: float) -> str:
    """An outcome-plane evidence ref whose OWN timestamp is ts_s (stream ids
    self-stamp in milliseconds -- the resolver derives, never trusts)."""
    return f"event:events:raw:{int(ts_s * 1000)}-0"


def _reg(tmp_path, now):
    clock = {"t": now}
    r = ForecastRegistry(path=str(tmp_path / "forecasts.jsonl"),
                         now_fn=lambda: clock["t"])
    return r, clock


def _register(r, fid="F001", by="claude", horizon=None):
    return r.register(
        id=fid, task_ref="T999", registered_by=by,
        expectation={"statement": "the suite stays green", "metric": "failures",
                     "target": 0},
        horizon_ts=horizon if horizon is not None else T0 + 3600,
        mechanism="pins gate the door",
        dies_when="the suite is retired")


# ------------------------------------------------------- P1 append-only + pure fold
def test_p1_duplicate_refused_log_only_grows_fold_is_pure(tmp_path):
    r, clock = _reg(tmp_path, T0)
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

    # the pure-fold seam: hand-built events, no file, input unmutated
    events = [{"kind": "register", "id": "X1", "registered_by": "a",
               "registered_at": T0, "horizon_ts": T0 + 10,
               "expectation": {"statement": "s"}, "task_ref": "T1",
               "mechanism": "m", "dies_when": "d"}]
    snapshot = [dict(e) for e in events]
    state = fold(events)
    assert state["X1"]["registered_by"] == "a"
    assert events == snapshot, "fold must not mutate its input"


# ------------------------------------------------- P2 derived ts, strictly after
def test_p2_knowable_ts_is_derived_strict_and_unforgeable(tmp_path):
    r, clock = _reg(tmp_path, T0)
    _register(r)                                        # registered_at == T0

    # the door cannot accept a claimed timestamp -- the parameter must not exist
    with pytest.raises(TypeError):
        r.score("F001", scored_by="claude", observed="green",
                evidence_ref=_ev_ref(T0 + 10), verdict="hit",
                outcome_knowable_ts=T0 + 10)

    # hindsight: evidence artifact OLDER than registration -> refuse
    with pytest.raises(RegistryRefusal) as exc:
        r.score("F001", scored_by="claude", observed="green",
                evidence_ref=_ev_ref(T0 - 60), verdict="hit")
    assert "hindsight" in str(exc.value).lower()

    # the == boundary refuses: strictly greater or it is not a forecast
    with pytest.raises(RegistryRefusal):
        r.score("F001", scored_by="claude", observed="green",
                evidence_ref=_ev_ref(T0), verdict="hit")

    # missing / unresolvable evidence refuses
    with pytest.raises(RegistryRefusal):
        r.score("F001", scored_by="claude", observed="green",
                evidence_ref="", verdict="hit")
    with pytest.raises(RegistryRefusal):
        r.score("F001", scored_by="claude", observed="green",
                evidence_ref="vibes:trust-me", verdict="hit")

    # clean: evidence strictly after registration scores, ts derived from ref
    clock["t"] = T0 + 100
    row = r.score("F001", scored_by="claude", observed="suite green",
                  evidence_ref=_ev_ref(T0 + 50), verdict="hit")
    assert row["outcome_knowable_ts"] == pytest.approx(T0 + 50)
    assert r.state()["F001"]["verdict"] == "hit"


# ------------------------------------------------------- P3 echo-ban + void carve-out
def test_p3_agreement_refused_except_the_void_carveout(tmp_path):
    r, clock = _reg(tmp_path, T0)
    _register(r)
    _register(r, fid="F002")

    with pytest.raises(RegistryRefusal) as exc:
        r.score("F001", scored_by="claude", observed="F002 agrees",
                evidence_ref="forecast:F002", verdict="hit")
    assert "agreement" in str(exc.value).lower() or "echo" in str(exc.value).lower()

    # the sole carve-out: a void is a statement about the bet, not credit
    row = r.score("F002", scored_by="claude", observed="instrument retired",
                  evidence_ref="forecast:F002", verdict="voided")
    assert r.state()["F002"]["verdict"] == "voided"
    assert row.get("outcome_knowable_ts") is None, \
        "a void claims nothing about when the world was knowable"


# ------------------------------------------------------- P4 calibration + enum
def test_p4_calibration_overdue_and_the_trader_member(tmp_path):
    assert "residual" in VERDICTS, \
        "the trader-inheritance member must exist in the enum from day one"

    r, clock = _reg(tmp_path, T0)
    _register(r, fid="F001", by="claude")
    _register(r, fid="F002", by="claude")
    _register(r, fid="F003", by="deepseek", horizon=T0 + 50)   # will go overdue
    clock["t"] = T0 + 100
    r.score("F001", scored_by="claude", observed="green",
            evidence_ref=_ev_ref(T0 + 20), verdict="hit")
    r.score("F002", scored_by="claude", observed="red",
            evidence_ref=_ev_ref(T0 + 20), verdict="miss")
    cal = r.calibration()
    assert cal["by_author"]["claude"]["hit"] == 1
    assert cal["by_author"]["claude"]["miss"] == 1
    assert cal["by_author"]["claude"]["rate"] == pytest.approx(0.5)
    assert [f["id"] for f in cal["overdue"]] == ["F003"], \
        "past-horizon unscored forecasts must surface, scored ones never"
