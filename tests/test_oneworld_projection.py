"""W0.1 pins -- the projection reader over the one-world journal (spec: atom d622ac, H9 section 1).

The claim this slice must PROVE, not assert: one authored world-state -> N projections, without
drift. A projection holds no state of its own; it is a pure fold of the journal, rebuilt on demand.
"Replay, don't diff" is only safe if a journal-rebuilt projection is IDENTICAL to a correct live one
and immune to the drift a live in-place surface suffers.

The sharpest test (P2) ties drift-freedom to the journal's idempotency: a crash-redelivered fact is
one line in the journal, so a projection rebuilt from it counts that fact ONCE. A naive live surface
that incremented on each arrival would count it twice -- that gap IS the drift, and rebuilding from
the authored truth closes it by construction.
"""
from __future__ import annotations

import pytest

journal = pytest.importorskip("core.oneworld.journal")
projection = pytest.importorskip("core.oneworld.projection")


@pytest.fixture
def jp(tmp_path, monkeypatch):
    p = tmp_path / "world.jsonl"
    monkeypatch.setattr(journal, "JOURNAL_PATH", p)
    return p


def test_latest_by_respects_authored_order(jp):
    journal.append("mode_set", "claude", {"surface": "fleet", "mode": "loud"})
    journal.append("mode_set", "claude", {"surface": "fleet", "mode": "quiet"})  # later wins
    journal.append("mode_set", "claude", {"surface": "floor", "mode": "loud"})
    r = projection.project(projection.latest_by(lambda f: f["payload"]["surface"]))
    state = r["state"]
    assert state["fleet"]["payload"]["mode"] == "quiet"   # the LATER fleet mode, not the first
    assert state["floor"]["payload"]["mode"] == "loud"


def test_redelivered_fact_counts_once_not_twice(jp):
    """The drift test. A double-written (crash-redelivered) fact is one journal line, so a
    projection rebuilt from the journal counts it ONCE. This is the drift a live in-place surface
    would suffer (it would count the arrival twice) and the one replay-from-authored-truth cannot."""
    journal.append("ev", "a", {"k": "x"})
    journal.append("ev", "a", {"k": "x"})   # identical content -> same id -> one line (idempotent)
    journal.append("ev", "a", {"k": "y"})
    r = projection.project(projection.count_by(lambda f: f["kind"]))
    assert r["state"]["ev"] == 2            # two DISTINCT facts, not three append calls


def test_projection_holds_no_state_wipe_and_rebuild(jp):
    """Build a surface, throw it away, rebuild from the journal alone -> identical. Wiping a
    derived surface loses nothing, because the journal is the truth (routes.py P5)."""
    for i in range(4):
        journal.append("ev", "a", {"n": i})
    red = projection.count_by(lambda f: f["kind"])
    first = projection.project(red)["state"]
    second = projection.project(red)["state"]   # a fresh rebuild, no carried state
    assert first == second == {"ev": 4}


def test_one_world_many_projections(jp):
    """One journal, two reducers, two independently-correct surfaces -- the N-projections claim."""
    journal.append("mode_set", "claude", {"surface": "fleet", "mode": "quiet"})
    journal.append("hail", "daniil", {"text": "walk day?"})
    journal.append("mode_set", "claude", {"surface": "floor", "mode": "loud"})
    # latest_by surface: the two mode_set facts key on their surface; the hail has none, so it keys
    # on its own id -- three distinct keys, each holding its latest fact.
    latest = projection.project(projection.latest_by(lambda f: f["payload"].get("surface") or f["id"]))
    counts = projection.project(projection.count_by(lambda f: f["kind"]))
    assert "fleet" in latest["state"] and "floor" in latest["state"]
    assert len(latest["state"]) == 3  # fleet, floor, and the hail (keyed by id)
    assert counts["state"] == {"mode_set": 2, "hail": 1}  # a different, equally-correct surface


def test_found_vs_taken_carried_into_projection(jp):
    """A corrupt journal line is reported as unparsed in the projection result, and the good facts
    are still projected -- the surface learns its projection was built over an imperfect journal."""
    journal.append("ev", "a", {"n": 1})
    with open(jp, "a", encoding="utf-8") as f:
        f.write("{ not json\n")
    journal.append("ev", "a", {"n": 2})
    r = projection.project(projection.count_by(lambda f: f["kind"]))
    assert r["state"] == {"ev": 2}
    assert r["taken"] == 2 and r["unparsed"] == 1


def test_empty_journal_projects_clean(jp):
    r = projection.project(projection.count_by(lambda f: f["kind"]))
    assert r["state"] == {} and r["taken"] == 0 and r["unparsed"] == 0
