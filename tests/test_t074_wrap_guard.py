"""T074 Phase 2 pins -- the wrap curated-guard (W7-W9 of the reconciled build spec,
docs/library/report/20260715_t074-seamless-continuity-reconciliation_89103c.md; deepseek's Rule 1-2
govern: the curated flag BEATS timestamp inference, and wrap must never let a
mechanical distillation silently supersede a hand-curated handoff -- the live
2026-07-15 clobber incident made unrepresentable).

BUILD REFINEMENTS (flagged, T073 precedent):
  R7  A LEGACY head (curated=None) is NOT guarded -- the flag beats inference both
      ways: we cannot prove curation, so we do not invent it (Phase-1 R1 sibling).
      Migration is organic: the next deliberate write through the note door stamps
      curated=True and the guard arms itself.
  R8  `wrap --focus` stamps next-focus curated=True: setting the directive is a
      DELIBERATE act (it feeds the whisper's DIRECTIVE line), not a distillation.
"""
import io
import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from core.learning import agent_memory as am
from core.foundation.store import FileStore


def _isolated_mem(monkeypatch):
    mem = am.AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    monkeypatch.setattr(am, "get_agent_memory", lambda: mem)
    # wrap's inputs quiet: no commits/lessons/flips so the draft is pure mechanics
    monkeypatch.setattr(agent_cli, "_recent_commits", lambda hours: [])
    monkeypatch.setattr(agent_cli, "_recent_lessons", lambda n: [])
    monkeypatch.setattr(agent_cli, "project_notes", lambda: "")
    return mem


def _args(**over):
    base = dict(hours=1, commit=True, title=None, focus=None, force=False)
    base.update(over)
    return SimpleNamespace(**base)


def _head(mem, title):
    return next((d for d in mem.get_decisions(days=365) if d.title == title), None)


# ---------------------------------------------------------------- W7 detect + refuse
def test_w7_mechanical_wrap_refuses_to_clobber_curated(monkeypatch, capsys):
    mem = _isolated_mem(monkeypatch)
    mem.decide("where-we-are", "HAND-CURATED HANDOFF: precious", curated=True)
    before = _head(mem, "where-we-are")
    rc = agent_cli.cmd_wrap(_args())
    out = capsys.readouterr().out
    assert rc == 1, "W7: the guarded wrap must refuse, loudly, not exit clean"
    assert "CURATED" in out and "--force" in out and "--title" in out, \
        f"W7: the refusal must teach both escape hatches, got: {out}"
    after = _head(mem, "where-we-are")
    assert after.id == before.id and after.decision == "HAND-CURATED HANDOFF: precious", \
        "W7: nothing may be written on refusal"


# ---------------------------------------------------------------- W8 --force
def test_w8_force_supersedes_deliberately(monkeypatch):
    mem = _isolated_mem(monkeypatch)
    mem.decide("where-we-are", "HAND-CURATED HANDOFF", curated=True)
    rc = agent_cli.cmd_wrap(_args(force=True))
    assert rc == 0
    head = _head(mem, "where-we-are")
    assert head.decision != "HAND-CURATED HANDOFF", "W8: --force supersedes"
    assert head.curated is False, "the wrap output stays honestly MECHANICAL even under --force"


# ---------------------------------------------------------------- W9 --title sidestep
def test_w9_title_records_alongside_curated_untouched(monkeypatch):
    mem = _isolated_mem(monkeypatch)
    mem.decide("where-we-are", "HAND-CURATED HANDOFF", curated=True)
    rc = agent_cli.cmd_wrap(_args(title="where-we-are-2026-07-15"))
    assert rc == 0
    assert _head(mem, "where-we-are").decision == "HAND-CURATED HANDOFF", "W9: curated head untouched"
    side = _head(mem, "where-we-are-2026-07-15")
    assert side is not None and side.curated is False


# ---------------------------------------------------------------- R7 legacy boundary
def test_r7_legacy_unflagged_head_is_not_guarded(monkeypatch):
    mem = _isolated_mem(monkeypatch)
    mem.decide("where-we-are", "legacy pre-flag note")          # curated=None
    rc = agent_cli.cmd_wrap(_args())
    assert rc == 0, "R7: no inference -- an unproven head is not protected"
    assert _head(mem, "where-we-are").decision != "legacy pre-flag note"


# ---------------------------------------------------------------- R8 focus is deliberate
def test_r8_focus_note_is_curated(monkeypatch):
    mem = _isolated_mem(monkeypatch)
    rc = agent_cli.cmd_wrap(_args(commit=True, focus="T074 Phase 3 next"))
    assert rc == 0
    nf = _head(mem, "next-focus")
    assert nf is not None and nf.curated is True, "R8: setting the directive is a deliberate act"
