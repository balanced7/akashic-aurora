"""Tests for the semantic drift check (core/narrative/drift) -- prototype.

Deterministic: `active` and `recent_beats` are passed explicitly, so nothing depends on the live
store or beat log. Covers the three drift modes + fail-open.
"""
from core.narrative.drift import _Cand, drift_check

UI = ["scripts/bifrost_ui.py"]


def test_coherent_when_action_routes_to_active_track():
    v = drift_check("collapse traces in bifrost_ui.py", paths=UI, active="ai-setup", recent_beats=[])
    assert v.coherent and v.kind == ""


def test_scope_drift_when_action_routes_elsewhere():
    # you think you're in 'research', but a bifrost_ui.py action routes to 'ai-setup'
    v = drift_check("collapse traces in bifrost_ui.py", paths=UI, active="research", recent_beats=[])
    assert not v.coherent and v.kind == "scope" and "different thread" in v.reason


def test_rework_on_near_duplicate_beat():
    # Jaccard word-overlap is the (tunable) rework signal; this pair is a clear near-dup (>0.6).
    past = [_Cand("collapse agent reasoning and tool traces into cards")]
    v = drift_check("collapse agent reasoning and tool traces into collapsible cards", paths=UI,
                    active="ai-setup", recent_beats=past)
    assert not v.coherent and v.kind == "rework"


def test_not_rework_when_unrelated():
    past = [_Cand("write the deployment runbook")]
    v = drift_check("collapse agent traces into cards", paths=UI, active="ai-setup", recent_beats=past)
    assert v.coherent


def test_fail_open_on_router_error():
    class Boom:
        def route_one(self, *a, **k):
            raise RuntimeError("spine down")
    v = drift_check("anything", active="ai-setup", recent_beats=[], router=Boom())
    assert v.coherent   # a drift-check machinery fault must NEVER block real work
