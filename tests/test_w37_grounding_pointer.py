"""W37/B6 pins — the grounding pointer (the wave's last slice; 6/6).

Tonight's boot proved the pattern: the outgoing seat's reflection doc was the single
best orientation artifact two boots running — but it exists only because Daniel ad-hoc
directed one. B6 canonizes it as substrate. Kimi amendments (their counter, all folded):
(a) the pointer carries written-at; boot stamps age — never grow W04's disease in a new
organ; (b) "keeps prior if fresh" spells its bound (GROUNDING_FRESH_DAYS) — nothing
keeps silently forever; (c) absence is DECLARED (--grounding none retires with a
receipt), never a silent forget. Renamed per kimi's naming pass: grounding-POINTER
(canon stays disposition vocabulary).

  P1  wrap --grounding <path> sets the pointer note (active head)
  P2  boot renders GROUND FIRST + [as of <date>] while fresh
  P3  an old pointer renders [STALE? Nd old] — aged, visible, still shown
  P4  --grounding none retires it with a receipt; boot drops the line
  P5  a fresh pointer survives a plain wrap --commit, with the kept-line printed
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


class Ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, k):
        return None


@pytest.fixture()
def mem(monkeypatch):
    m = AgentMemory(store=DictStore())
    monkeypatch.setattr("core.learning.agent_memory.get_agent_memory", lambda: m)
    monkeypatch.setattr("core.coord.task_ledger.state_view", lambda *a, **k: {})
    monkeypatch.setattr(agent_cli, "_recent_commits", lambda h: [])
    monkeypatch.setattr(agent_cli, "_recent_lessons", lambda n: [])
    return m


def _forge(mem, dec_id, title, body, created):
    d = Decision(id=dec_id, title=title, status="accepted", context="", decision=body,
                 rationale=[], alternatives=[], consequences={"positive": [], "negative": []},
                 created_at=created, session_id="")
    mem.store.hset(mem.KEY_DECISIONS, field=dec_id, value=json.dumps(asdict(d)))
    mem.store.zadd(mem.KEY_DECISION_INDEX,
                   {dec_id: datetime.fromisoformat(created).timestamp()})


def _pointer(mem):
    return [d for d in mem.get_decisions(days=3650)
            if d.title == "grounding-pointer" and not d.superseded]


def _wrap(commit=False, grounding=None, hours=12):
    return Ns(hours=hours, commit=commit, grounding=grounding, focus=None,
              title=None, force=False)


def test_p1_wrap_sets_pointer(mem, capsys):
    rc = agent_cli.cmd_wrap(_wrap(grounding="chronicles/reflection-x.md"))
    assert rc == 0
    live = _pointer(mem)
    assert len(live) == 1 and "chronicles/reflection-x.md" in live[0].decision
    assert "grounding pointer set" in capsys.readouterr().out


def test_p2_boot_renders_fresh_pointer(mem):
    _forge(mem, "ADR_gp_fresh", "grounding-pointer", "chronicles/reflection-x.md",
           datetime.now().isoformat())
    head = agent_cli._orientation_header("claude")
    assert "GROUND FIRST: chronicles/reflection-x.md" in head
    assert f"[as of {datetime.now().isoformat()[:10]}]" in head
    assert "STALE?" not in head.split("GROUND FIRST")[1].splitlines()[0]


def test_p3_old_pointer_confesses_age(mem):
    old = (datetime.now() - timedelta(days=12)).isoformat()
    _forge(mem, "ADR_gp_old0", "grounding-pointer", "chronicles/old-voice.md", old)
    head = agent_cli._orientation_header("claude")
    line = [l for l in head.splitlines() if "GROUND FIRST" in l][0]
    assert "chronicles/old-voice.md" in line and "STALE?" in line and "12d" in line


def test_p4_declared_absence(mem, capsys):
    _forge(mem, "ADR_gp_ret0", "grounding-pointer", "chronicles/x.md",
           datetime.now().isoformat())
    rc = agent_cli.cmd_wrap(_wrap(grounding="none"))
    assert rc == 0
    assert _pointer(mem) == [], "declared none retires the pointer"
    assert "declared" in capsys.readouterr().out.lower()
    assert "GROUND FIRST" not in agent_cli._orientation_header("claude")


def test_p5_fresh_pointer_survives_commit(mem, capsys):
    _forge(mem, "ADR_gp_keep", "grounding-pointer", "chronicles/keep-me.md",
           (datetime.now() - timedelta(days=2)).isoformat())
    rc = agent_cli.cmd_wrap(_wrap(commit=True))
    assert rc == 0
    assert len(_pointer(mem)) == 1, "fresh pointer kept"
    assert "grounding pointer kept" in capsys.readouterr().out
