"""W04 pins — the CURRENT DIRECTIVE line confesses its age and defers to the ledger.

Wish W04 (kimi 07-18; THIRD bite 07-21: the 2026-07-15 morning-gate banner rode boot as
"do this FIRST" for three consecutive seats, each re-diagnosing it stale by hand).
A banner that outlives its work must confess, not command:
  P1  fresh directive renders [as of <date>], no stale tag
  P2  an old directive renders [STALE? <n>d old]
  P3  a directive naming a ledger-DONE task renders [LEDGER DISAGREES: ... trust the ledger]
  P4  ledger unreachable = fail-open (directive renders, no DISAGREES tag, no crash)

(The ROOT-CAUSE half — wrap superseding next-focus — is W36, held for the deepseek
counter per the night-consensus protocol; this stamp half is pure information-add.)
"""
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import DictStore
from core.learning.agent_memory import AgentMemory, Decision

import agent_cli


@pytest.fixture()
def mem(monkeypatch):
    m = AgentMemory(store=DictStore())
    monkeypatch.setattr("core.learning.agent_memory.get_agent_memory", lambda: m)
    monkeypatch.setattr("core.coord.task_ledger.state_view", lambda *a, **k: {})
    return m


def _forge_note(mem, dec_id, title, body, created):
    d = Decision(id=dec_id, title=title, status="accepted", context="", decision=body,
                 rationale=[], alternatives=[], consequences={"positive": [], "negative": []},
                 created_at=created, session_id="")
    mem.store.hset(mem.KEY_DECISIONS, field=dec_id, value=json.dumps(asdict(d)))
    mem.store.zadd(mem.KEY_DECISION_INDEX,
                   {dec_id: datetime.fromisoformat(created).timestamp()})


def test_p1_fresh_directive_stamped_not_stale(mem):
    now = datetime.now()
    _forge_note(mem, "ADR_nf_fresh000", "next-focus", "build the next slice",
                now.isoformat())
    head = agent_cli._orientation_header("claude")
    assert f"[as of {now.isoformat()[:10]}]" in head
    assert "STALE?" not in head


def test_p2_old_directive_flagged(mem):
    old = datetime.now() - timedelta(days=10)
    _forge_note(mem, "ADR_nf_old00000", "next-focus", "approve the old wave",
                old.isoformat())
    head = agent_cli._orientation_header("claude")
    assert "[STALE?" in head and "d old" in head


def test_p3_ledger_done_task_disagrees(mem, monkeypatch):
    monkeypatch.setattr(
        "core.coord.task_ledger.state_view",
        lambda *a, **k: {"done": [{"id": "T075", "status": "done"}],
                         "active": [{"id": "T099", "status": "claimed"}]})
    _forge_note(mem, "ADR_nf_done0000", "next-focus",
                "approve/amend T075 M1 build wave", datetime.now().isoformat())
    head = agent_cli._orientation_header("claude")
    assert "LEDGER DISAGREES" in head and "T075 DONE" in head and "trust the ledger" in head


def test_p5_parked_task_also_disagrees(mem, monkeypatch):
    # kimi B1(c) fence finding (live receipt: the 07-15 banner names PARKED T075 and the
    # DONE-only check stayed silent): parked and abandoned CONTRADICT do-this-FIRST too.
    monkeypatch.setattr(
        "core.coord.task_ledger.state_view",
        lambda *a, **k: {"parked": [{"id": "T075", "status": "parked"}],
                         "active": [{"id": "T071", "status": "claimed"}]})
    _forge_note(mem, "ADR_nf_park0000", "next-focus",
                "approve/amend T075 M1 build wave + T071 verdicts",
                datetime.now().isoformat())
    head = agent_cli._orientation_header("claude")
    assert "T075 PARKED" in head and "LEDGER DISAGREES" in head
    assert "T071" not in head.split("LEDGER DISAGREES")[1].split("]")[0], \
        "an ACTIVE named task never rides the disagreement tag"


def test_p4_ledger_down_fails_open(mem, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("redis down")
    monkeypatch.setattr("core.coord.task_ledger.state_view", boom)
    _forge_note(mem, "ADR_nf_failopen", "next-focus",
                "verify T031 enforcement", datetime.now().isoformat())
    head = agent_cli._orientation_header("claude")
    assert "verify T031 enforcement" in head
    assert "LEDGER DISAGREES" not in head
