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


def test_research_refused_after_p3_flip():
    # P3 fired 2026-07-23 ("Delete the 643!"): research births go through the door now.
    assert bg.classify("research/drafts/seat-topic-2026-07-24.md") == "refuse"
    assert bg.classify("research/anything.md") == "refuse"


def test_chronicles_machinery_allowlist_after_p3b():
    for f in ("memory.md", "last-session-draft.md", "lessons.md", "story.md"):
        assert bg.classify(f"chronicles/{f}") == "allow"
    assert bg.classify("chronicles/night-plan-2026-07-24.md") == "refuse"
    assert bg.classify("chronicles/session-reflection-x.md") == "refuse"


def test_charter_lawful_home_allowed_loose_warned():
    assert bg.classify("charters/kimi/CHARTER.md") == "allow"
    assert bg.classify("charters/new-loose-charter.md") == "warn"


def test_non_md_untouched():
    assert bg.classify("core/library/atoms.py") == "allow"
    assert bg.classify("store/docs/report.jsonl") == "allow"
