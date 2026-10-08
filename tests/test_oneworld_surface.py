"""W-surface pins -- the standalone world-view adapter (spec d622ac; Daniel's live+agent-aware ask).

surface.agents_view assembles a serializable presence payload from a roster source. It is the "what
to show" half; Heimdall wires the "how to serve it" (serve.py endpoint, browser, streaming).

The load-bearing contract is the SAME honesty the floor enforces: a roster read that FAILS must
report `unavailable`, never an empty agent list -- "nobody is online" and "I could not see the
roster" are different facts, and a live dashboard that renders the second as the first is lying at
exactly the moment the house is in trouble (zero is not no). The presence source is injectable so
this is pinned without a live Redis.
"""
from __future__ import annotations

import pytest

surface = pytest.importorskip("core.oneworld.surface")


def _src(rows):
    return lambda: list(rows)


def test_agents_view_lists_normalized_agents():
    v = surface.agents_view(presence_source=_src([
        {"agent": "claude", "state": "LIVE", "phase": "running", "beat_age_s": 1.9},
        {"agent": "deepseek", "state": "LIVE", "phase": "running", "beat_age_s": 2.1},
    ]))
    assert v["ok"] is True
    assert {a["agent"] for a in v["agents"]} == {"claude", "deepseek"}
    assert all({"agent", "state", "phase", "beat_age_s"} <= set(a) for a in v["agents"])
    assert v["bounds"].strip() and v["as_of"]


def test_missing_phase_or_beat_is_named_not_dropped():
    v = surface.agents_view(presence_source=_src([
        {"agent": "rill", "state": "OFFLINE"},  # no phase, no beat
    ]))
    assert any(a["agent"] == "rill" for a in v["agents"]), "an incomplete row is kept, not dropped"
    assert "complete" not in v["bounds"].lower(), "the gap must be named in the legend"


def test_source_unavailable_is_not_an_empty_roster():
    def boom():
        raise RuntimeError("redis down")
    v = surface.agents_view(presence_source=boom)
    assert v["ok"] is False
    assert v["agents"] == []
    assert "unavailable" in v["bounds"].lower(), "blind must read as unavailable, not 'nobody online'"


def test_genuinely_empty_roster_is_distinct_from_unavailable():
    v = surface.agents_view(presence_source=_src([]))
    assert v["ok"] is True
    assert v["agents"] == []
    assert "unavailable" not in v["bounds"].lower(), "checked-and-empty is not blind"


def test_view_is_a_pure_function_of_its_source():
    s = _src([{"agent": "claude", "state": "LIVE", "phase": "running", "beat_age_s": 1.0}])
    assert surface.agents_view(presence_source=s)["agents"] == \
        surface.agents_view(presence_source=s)["agents"]
