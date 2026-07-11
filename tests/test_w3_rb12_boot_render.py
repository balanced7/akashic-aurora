"""
Wave 3 / RB-12 -- boot-render integration pins, landed WITH the impl commit as promised
by tests/test_w3_rb11_rb12.py's header ("[GAP] lines are integration-pinned in the RB-12
impl commit itself" -- they need the agent_cli render layer, so they could not be
pre-registered against a not-yet-existing render).

Scope: _orientation_header (importable + deterministic). The RECENT-NOTES [GAP] line in
cmd_boot prints inside the boot verb and is exercised by the same empty-notes branch;
a subprocess-level boot drill is deliberately out of scope here.

Also pins the 2026-07-11 wake-verify ruling: governing-arc candidate selection stays
NEWEST-wins, inherited from get_decisions()'s (created_at, title, id) total order. An
alphabetical pre-sort (the review's draft remedy against the old single-key sort) must
never override recency -- it made the fallback's "newest is" line lie.

Run: py -m pytest tests/test_w3_rb12_boot_render.py -q
"""
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import DictStore
from core.learning.agent_memory import AgentMemory, Decision

import agent_cli


@pytest.fixture()
def mem(monkeypatch):
    m = AgentMemory(store=DictStore())
    monkeypatch.setattr("core.learning.agent_memory.get_agent_memory", lambda: m)
    # hermetic: no live task ledger -- forged slugs must never match real active tasks
    monkeypatch.setattr("core.coord.task_ledger.state_view", lambda: {})
    return m


def _forge_note(mem, dec_id, title, body, created):
    d = Decision(id=dec_id, title=title, status="accepted", context="", decision=body,
                 rationale=[], alternatives=[], consequences={"positive": [], "negative": []},
                 created_at=created, session_id="")
    mem.store.hset(mem.KEY_DECISIONS, field=dec_id, value=json.dumps(asdict(d)))
    mem.store.zadd(mem.KEY_DECISION_INDEX,
                   {dec_id: datetime.fromisoformat(created).timestamp()})


def test_empty_store_renders_gap_lines_not_crash(mem):
    head = agent_cli._orientation_header("claude")
    assert "[GAP] Governing arc:" in head
    assert "[GAP] where-we-are:" in head
    assert "[GAP] CURRENT DIRECTIVE:" in head


def test_gap_lines_replaced_when_notes_exist(mem):
    _forge_note(mem, "ADR_wwa_00000001", "where-we-are", "mid-wave-3",
                datetime(2026, 7, 10).isoformat())
    _forge_note(mem, "ADR_nf_00000002", "next-focus", "verify RB-9..12",
                datetime(2026, 7, 10).isoformat())
    head = agent_cli._orientation_header("claude")
    assert "[GAP] where-we-are:" not in head and "mid-wave-3" in head
    assert "[GAP] CURRENT DIRECTIVE:" not in head and "verify RB-9..12" in head


def test_fallback_arc_is_newest_not_alphabetical(mem):
    # alpha-by-doc-path would pick docs/aaa-old.md; recency must pick docs/zzz-new.md
    _forge_note(mem, "ADR_old_00000001", "qqold-arc-status",
                "older arc, doc docs/aaa-old.md", datetime(2026, 7, 1).isoformat())
    _forge_note(mem, "ADR_new_00000002", "qqnew-arc-status",
                "newer arc, doc docs/zzz-new.md", datetime(2026, 7, 10).isoformat())
    head = agent_cli._orientation_header("claude")
    assert "newest is docs/zzz-new.md" in head, \
        "the fallback names the NEWEST candidate, never the alphabetically-first"
