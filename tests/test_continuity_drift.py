"""Continuity-drift detection (2026-07-25).

WHY IT EXISTS. Three of the four continuity organs were stale AT ONCE -- GROUND FIRST aimed
at a two-day-old chronicle, where-we-are trailing four commits, the directive naming a
superseded plan -- and nothing said so. The seat found out by looking.

The asymmetry it closes: retrieval is automatic (recall-at fires unasked at every action,
and it is the organ that works); capture is manual (wrap/note/--grounding wait for a seat to
remember). A continuity layer that depends on remembering goes stale exactly when a session
was too busy to remember, which is when it matters most.

It detects; it never writes. The corpus already grows at ~13.7x its own target rate with
flat measured value, so auto-generating content would add noise to a system whose problem is
not scarcity. Tonight's failures were stale POINTERS to content that existed -- so the
automation belongs on the pointer, not the payload.

  D1  notes OLDER than HEAD -> the drift line fires and names them
  D2  notes NEWER than HEAD -> SILENT (no drift, no line -- this is the noise constraint)
  D3  a MISSING organ is named too (absent is a worse drift than stale)
  D4  no git / no HEAD -> silent, never raises (fail-soft; boot must not break)
  D5  the line does NOT spend the head-16 the cold-start contract owns
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


class _Note:
    def __init__(self, title, created_at):
        self.title = title
        self.created_at = created_at
        self.superseded = None


def _iso(epoch):
    from datetime import datetime
    return datetime.fromtimestamp(epoch).isoformat()


ALL = ("where-we-are", "next-focus", "grounding-pointer")


def test_d1_stale_notes_fire_the_drift_line(monkeypatch):
    head = time.time()
    monkeypatch.setattr(agent_cli, "_head_commit_epoch", lambda: head)
    old = [_Note(t, _iso(head - 86400)) for t in ALL]          # a day behind HEAD
    line = agent_cli._continuity_drift(notes=old)
    assert "continuity DRIFT" in line
    for t in ALL:
        assert t in line, f"{t} must be named so the seat knows WHICH organ lags"


def test_d2_fresh_notes_are_silent(monkeypatch):
    """The noise constraint, pinned. An organ that speaks when nothing is wrong trains
    every seat to skim it -- which is how the heal banner earned W64."""
    head = time.time() - 86400
    monkeypatch.setattr(agent_cli, "_head_commit_epoch", lambda: head)
    fresh = [_Note(t, _iso(time.time())) for t in ALL]
    assert agent_cli._continuity_drift(notes=fresh) == ""


def test_d3_missing_organ_is_named(monkeypatch):
    head = time.time()
    monkeypatch.setattr(agent_cli, "_head_commit_epoch", lambda: head)
    only_one = [_Note("where-we-are", _iso(time.time()))]
    line = agent_cli._continuity_drift(notes=only_one)
    assert "next-focus MISSING" in line and "grounding-pointer MISSING" in line
    # the FRESH organ must not be reported as drifting. Assert on the named-drift list
    # only -- the remediation tail legitimately mentions where-we-are as a fix command.
    named = line.split("written:")[1].split("--")[0]
    assert "where-we-are" not in named, "a fresh organ is not drift"


def test_d4_no_git_is_silent_and_never_raises(monkeypatch):
    monkeypatch.setattr(agent_cli, "_head_commit_epoch", lambda: None)
    assert agent_cli._continuity_drift(notes=[_Note(t, _iso(0)) for t in ALL]) == ""


def test_d5_drift_line_does_not_spend_the_head16():
    """new_boot_organ_must_not_spend_head16, filed hours before this organ was built.
    The four cold-start questions own the first 16 lines; a new organ earns its way in
    without displacing a proven one."""
    head = agent_cli._orientation_header("claude")
    first16 = "\n".join(head.splitlines()[:16])
    assert "continuity DRIFT" not in first16
