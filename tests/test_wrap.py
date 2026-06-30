"""Tests for wrap's session-draft builder -- ambient capture distills the session's OWN activity
(commits + lessons + notes) into a DRAFT where-we-are, each line keeping a lossless source pointer.

Run: py tests/test_wrap.py   (or via pytest)
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


def test_draft_has_sections_and_pointers():
    commits = [("abc123", "ship: one-command gated slice"), ("def456", "wrap: ambient capture")]
    lessons = [{"experiment_name": "write_once_notes_shipped", "recommendation": "record once, reproject"}]
    notes = [SimpleNamespace(id="ADR_1", title="next-focus", decision="FC-01 curator is next")]
    d = agent_cli.build_session_draft(commits, lessons, notes)
    assert "Shipped:" in d and "Learned:" in d and "Decided / noted:" in d, d
    assert "(git:abc123)" in d and "(learn:experiment:write_once_notes_shipped)" in d and "(mem:decision:ADR_1)" in d, d
    assert "ship: one-command gated slice" in d and "next-focus" in d, d
    print("\n--- draft sections + pointers ---\n  Shipped/Learned/Decided with source pointers OK")


def test_empty_session_draft():
    assert agent_cli.build_session_draft([], [], []) == "(no session activity captured)"
    print("--- empty ---\n  no activity -> honest empty draft OK")


def test_caps_per_section():
    commits = [(f"sha{i}", f"commit {i}") for i in range(20)]
    d = agent_cli.build_session_draft(commits, [], [], max_per=5)
    assert d.count("(git:") == 5, "caps each section at max_per"
    print("--- caps ---\n  per-section cap respected OK")


if __name__ == "__main__":
    print("=" * 60)
    print("WRAP DRAFT TESTS")
    print("=" * 60)
    test_draft_has_sections_and_pointers()
    test_empty_session_draft()
    test_caps_per_section()
    print("\n" + "=" * 60)
    print("ALL WRAP TESTS PASSED")
    print("=" * 60)
