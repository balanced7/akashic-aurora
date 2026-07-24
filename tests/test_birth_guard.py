"""Pins for the rule-13 birth guard's pure classification rule (A1)."""

import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "birth_guard",
    os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks", "birth_guard.py"))
bg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bg)


def test_projections_and_crown_allowed():
    assert bg.classify("docs/library/report/20260723_x_ab12cd.md") == "allow"
    assert bg.classify("docs/LIBRARY.md") == "allow"
    assert bg.classify("docs/LIVE_CONSTRAINTS.md") == "allow"
    assert bg.classify("docs/_archive/old-thing.md") == "allow"
    assert bg.classify("research/README.md") == "allow"
    assert bg.classify("README.md") == "allow"


def test_new_loose_docs_md_refused():
    assert bg.classify("docs/my-new-design-2026-07.md") == "refuse"
    assert bg.classify("docs/sub/thing.md") == "refuse"


def test_research_chronicles_warn_during_migration_window():
    assert bg.classify("research/drafts/seat-topic-2026-07-24.md") == "warn"
    assert bg.classify("chronicles/night-plan.md") == "warn"
    assert bg.classify("charters/new-charter.md") == "warn"


def test_non_md_untouched():
    assert bg.classify("core/library/atoms.py") == "allow"
    assert bg.classify("store/docs/report.jsonl") == "allow"
