"""Arch-slice loader (context/arch_loader.py) -- RENEW Strand E gap #2.

Deterministic ORIENTATION: project the stable architecture map down to the subsystems relevant to a
task. The acceptance bar is precision (right task -> right subsystem + path) and the show-nothing floor
(an unrelated task orients on NOTHING rather than surfacing an off-topic map -- context-rot discipline).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.context.arch_loader import load_arch_slice, _parse_sections, _repo_docs_dir


def _headings(rows):
    return " | ".join(r["heading"] for r in rows)


# --- precision: the right task orients on the right subsystem, top-ranked, with its code path -------

def test_bifrost_task_surfaces_bifrost_subsystem_first():
    rows = load_arch_slice("bifrost bus runner lock supervision wake doorbell")
    assert rows, "a clearly-matching task must produce an arch slice"
    assert "Bifrost" in rows[0]["heading"]
    assert rows[0]["path"] == "core/comm/"
    assert rows[0]["source"] == "docs/ARCHITECTURE.md"


def test_coordination_task_surfaces_coord_subsystem_first():
    rows = load_arch_slice("task ledger coordination conductor negotiation")
    assert rows and rows[0]["path"] == "core/coord/", _headings(rows)


def test_foundation_task_surfaces_foundation_first():
    rows = load_arch_slice("store ledger redis reconcile foundation persistence")
    assert rows and rows[0]["path"] == "core/foundation/", _headings(rows)


# --- show-nothing floor: silence beats an off-topic map --------------------------------------------

def test_unrelated_task_orients_on_nothing():
    assert load_arch_slice("xyzzy nonsense unrelated flibbertigibbet") == []


def test_empty_task_orients_on_nothing():
    assert load_arch_slice("") == []
    assert load_arch_slice("   ") == []


# --- projection hygiene: only real subsystems (path >= 2 segments), never meta sections ------------

def test_only_subsystem_sections_are_targets():
    rows = load_arch_slice("core knowledge memory learning recall bifrost coordination foundation events",
                           top_k=20, min_relevance=0.0)
    headings = _headings(rows).lower()
    # meta sections must never be orientation targets
    assert "where to start reading" not in headings
    assert "anti-rot" not in headings and "how this map stays alive" not in headings
    assert "the layer stack" not in headings
    # every surfaced row carries a real, deeper-than-root code path
    for r in rows:
        assert r["path"].count("/") >= 2, r


def test_topk_and_relevance_are_respected():
    rows = load_arch_slice("bifrost coordination foundation store ledger recall memory", top_k=2)
    assert len(rows) <= 2


# --- fail-soft: a missing/renamed doc degrades to [], never raises ---------------------------------

def test_missing_docs_dir_is_empty_not_error(tmp_path):
    assert load_arch_slice("bifrost bus", docs_dir=str(tmp_path)) == []


def test_parse_sections_reads_the_real_map():
    secs = _parse_sections(os.path.join(_repo_docs_dir(), "ARCHITECTURE.md"))
    assert any(s["path"] == "core/comm/" for s in secs), "the real map should parse a Bifrost path"
