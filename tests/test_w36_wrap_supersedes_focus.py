"""W36 pins — wrap retires the stale CURRENT DIRECTIVE (the three-bite root cause).

Consensus: claude opening + kimi counter AGREE (Q1: auto-with-tombstone, no exemptions);
kimi blocking amendments folded: (a) ORDERING — the new where-we-are lands BEFORE the old
next-focus is touched; a wrap that fails mid-way never leaves boot with [GAP] as its only
directive state; (b) RECEIPT — retirement prints loudly; silent retirement is how the
07-15 banner bit three seats. Scope guard: ONLY the next-focus title family.

Freshness rule: a next-focus OLDER than the wrap's own look-back window (--hours,
default 12) is presumptively consumed by the session being wrapped -> retired. One set
WITHIN the window is fresh intent (possibly another seat's) -> survives.

  P1  stale next-focus retired on wrap --commit; receipt line printed; wwa written
  P2  ORDERING: a refused where-we-are write (curated head, no --force) touches nothing
  P3  a fresh next-focus (inside the window) survives the wrap
  P4  wrap --commit --focus "new" supersedes old focus with NEW intent (never a bare gap)
  P5  no next-focus at all -> wrap works, no receipt, no crash
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
    monkeypatch.setattr(agent_cli, "_recent_commits", lambda h: [])
    monkeypatch.setattr(agent_cli, "_recent_lessons", lambda n: [])
    return m


def _forge_note(mem, dec_id, title, body, created, curated=None):
    d = Decision(id=dec_id, title=title, status="accepted", context="", decision=body,
                 rationale=[], alternatives=[], consequences={"positive": [], "negative": []},
                 created_at=created, session_id="")
    rec = asdict(d)
    if curated is not None:
        rec["curated"] = curated
    mem.store.hset(mem.KEY_DECISIONS, field=dec_id, value=json.dumps(rec))
    mem.store.zadd(mem.KEY_DECISION_INDEX,
                   {dec_id: datetime.fromisoformat(created).timestamp()})
    mem.store.set(mem.HEAD_KEY_PREFIX + title, dec_id) if hasattr(mem, "HEAD_KEY_PREFIX") else None


def _active_focus(mem):
    return [d for d in mem.get_decisions(days=3650)
            if d.title == "next-focus" and not d.superseded]


def _wrap(commit=True, focus=None, hours=12, force=False):
    return Ns(hours=hours, commit=commit, focus=focus, title=None, force=force)


def test_p1_stale_focus_retired_with_receipt(mem, capsys):
    old = (datetime.now() - timedelta(days=5)).isoformat()
    _forge_note(mem, "ADR_nf_stale", "next-focus", "MORNING GATE: approve T075", old)
    rc = agent_cli.cmd_wrap(_wrap())
    assert rc == 0
    out = capsys.readouterr().out
    assert _active_focus(mem) == [], "stale next-focus retired"
    assert "retired stale next-focus" in out and "ADR_nf_stale" in out, \
        "the retirement is a LOUD receipt, never silent"
    assert any(d.title == "where-we-are" for d in mem.get_decisions(days=1)), \
        "the wrap's own note landed"


def test_p2_refused_wrap_touches_nothing(mem, capsys):
    old = (datetime.now() - timedelta(days=5)).isoformat()
    _forge_note(mem, "ADR_nf_stale2", "next-focus", "old directive", old)
    _forge_note(mem, "ADR_wwa_cur", "where-we-are", "hand-written state",
                datetime.now().isoformat(), curated=True)
    rc = agent_cli.cmd_wrap(_wrap(force=False))
    assert rc == 1, "curated head refuses the mechanical wrap"
    assert len(_active_focus(mem)) == 1, \
        "ORDERING pin: a refused wrap never tombstones the only directive"


def test_p3_fresh_focus_survives(mem, capsys):
    fresh = (datetime.now() - timedelta(hours=2)).isoformat()
    _forge_note(mem, "ADR_nf_fresh", "next-focus", "tonight: build B3", fresh)
    rc = agent_cli.cmd_wrap(_wrap(hours=12))
    assert rc == 0
    assert len(_active_focus(mem)) == 1, \
        "a directive set within the wrap window is fresh intent -- survives"


def test_p4_focus_flag_replaces_not_gaps(mem, capsys):
    old = (datetime.now() - timedelta(days=5)).isoformat()
    _forge_note(mem, "ADR_nf_old4", "next-focus", "old directive", old)
    rc = agent_cli.cmd_wrap(_wrap(focus="NEW: ship the wave"))
    assert rc == 0
    live = _active_focus(mem)
    assert len(live) == 1 and "NEW: ship the wave" in live[0].decision, \
        "--focus supersedes with fresh intent; the slot never gaps"


def test_p5_no_focus_no_crash(mem, capsys):
    rc = agent_cli.cmd_wrap(_wrap())
    assert rc == 0
    assert "retired stale next-focus" not in capsys.readouterr().out
