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


def test_write_last_session_draft_to_file():
    import tempfile
    d = tempfile.mkdtemp()
    path = os.path.join(d, "chronicles", "last-session-draft.md")
    commits = [("abc123", "ship: gated slice")]
    lessons = [{"experiment_name": "e1", "recommendation": "r1"}]
    notes = [SimpleNamespace(id="ADR_1", title="next-focus", decision="FC-01")]
    out = agent_cli.write_last_session_draft(path, commits, lessons, notes, trigger="PreCompact")
    assert out == path and os.path.exists(path), "draft file is written"
    text = open(path, encoding="utf-8").read()
    assert "Last-session draft" in text and "PreCompact" in text, text[:120]
    assert "(git:abc123)" in text and "next-focus" in text, "draft body + pointers present"
    # no activity -> no file, returns None (don't write an empty draft)
    p2 = os.path.join(d, "chronicles", "empty.md")
    assert agent_cli.write_last_session_draft(p2, [], [], []) is None and not os.path.exists(p2)
    print("--- write draft file ---\n  auto-capture writes a draft file with header + pointers; empty -> None OK")


if __name__ == "__main__":
    print("=" * 60)
    print("WRAP DRAFT TESTS")
    print("=" * 60)
    test_draft_has_sections_and_pointers()
    test_empty_session_draft()
    test_caps_per_section()
    test_write_last_session_draft_to_file()
    print("\n" + "=" * 60)
    print("ALL WRAP TESTS PASSED")
    print("=" * 60)
