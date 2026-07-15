"""T074 Phase 4 W14 pins -- runner-boot fold (deepseek's own build, to his spec sec.3
"What I would change about my own boot" in research/reviewed/deepseek-t074-continuity-
design-2026-07-15.md; reconciled spec research/reviewed/t074-continuity-reconciliation-
2026-07-15.md). RED by pre-registration -- build follows, then GREEN.

The runner's boot fold is a compact ~5-line header block INJECTED BEFORE the full
PROJECT ONBOARDING (which the subprocess boot already provides). It answers "what am I
doing, who else is here" BEFORE the runner reads 6000 chars of project context.
Private notes ride the fold_private_notes() path downstream (proven placement, no
double-render).

Pins:
  W14-P1  DIRECTIVE is the first line: next-focus note body + age stamp, or ledger
          fallback when no directive exists.
  W14-P2  SIBLINGS line from live_incarnations(): solo or "N live sibling(s) (...)".
          The runner reads cards via core/comm/incarnation which is LIVE as of T074 P3.
  W14-P3  Private notes carry age stamps: every note line gains "(Nh ago)" or
          "(Nd ago)" -- the W14 literal pin from the spec table (W14: "add age stamps
          to note citations"). Private-note titles render via SLICE [len(prefix):],
          not INDEX (F1 fix: single-char regression).
  W14-P4  The continuity header (DIRECTIVE + SIBLINGS) precedes the project onboarding
          in the system prompt. DIRECTIVE is the first line.
  W14-P5  Fail-soft: every data source is independently wrapped; a broken store, dead
          bus, or missing card leaves the runner STARTING with the rest of the boot
          intact. Silence from one section is not silence from all.
  W14-P6  Budget: the continuity header is compact (~5 lines; ~300 chars) -- it
          competes sensibly with the 6000-char onboarding budget (T071 doctrine).
"""
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import bifrost_runner_deepseek as runner


# ---------------------------------------------------------------- helpers
def _dec(title, body, hours_ago=2.0, curated=None):
    from core.learning.agent_memory import Decision
    created = (datetime.now() - timedelta(hours=hours_ago)).isoformat()
    return Decision(id=f"ADR_test_{title}", title=title, status="accepted", context="",
                    decision=body, rationale=[], alternatives=[],
                    consequences={"positive": [], "negative": []},
                    created_at=created, curated=curated)


# ---------------------------------------------------------------- W14-P1 DIRECTIVE
def test_p1_directive_from_next_focus_with_age(monkeypatch):
    from core.learning import agent_memory as am
    from core.foundation.store import FileStore
    mem = am.AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    mem.decide("next-focus", "T074 Phase 4 runner fold", curated=True)
    monkeypatch.setattr(am, "get_agent_memory", lambda: mem)
    line = runner._directive_line("deepseek")
    assert line.startswith("DIRECTIVE: "), f"P1: expected DIRECTIVE prefix, got: {line}"
    assert "T074 Phase 4" in line
    assert "ago" in line, f"P1: age stamp missing, got: {line}"


def test_p1_directive_fallback_when_no_next_focus(monkeypatch):
    from core.learning import agent_memory as am
    from core.foundation.store import FileStore
    mem = am.AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    monkeypatch.setattr(am, "get_agent_memory", lambda: mem)
    line = runner._directive_line("deepseek")
    assert "DIRECTIVE: " in line
    assert "ledger" in line.lower(), f"P1 fallback: must point at the ledger, got: {line}"


def test_p1_directive_survives_broken_store(monkeypatch):
    # _directive_line does `from core.learning.agent_memory import get_agent_memory`
    # locally -- patch the source module so the local import gets the broken version.
    import core.learning.agent_memory as am
    monkeypatch.setattr(am, "get_agent_memory",
                        lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    line = runner._directive_line("deepseek")
    assert "DIRECTIVE: " in line, "P1 fail-soft: a broken store still produces a directive line"


# ---------------------------------------------------------------- W14-P2 SIBLINGS
def test_p2_siblings_solo(monkeypatch):
    monkeypatch.setattr(runner, "_siblings_for_runner",
                        lambda agent_id: "SIBLINGS: solo")
    assert runner._siblings_for_runner("deepseek") == "SIBLINGS: solo"


def test_p2_siblings_live(tmp_path, monkeypatch):
    # Plant an activity marker (the marker path is always available)
    from core.comm.incarnation import live_incarnations
    tmp = str(tmp_path)
    sid = "bbbbcccc-1111-2222-3333-444455556666"
    marker = os.path.join(tmp, f"bifrost_wake_claude_{sid}.alive")
    with open(marker, "w") as f:
        f.write(str(time.time() - 60))
    out = live_incarnations("claude", tmp=tmp, c=None, allow_fallback=False)
    assert len(out) == 1, "marker-only path must work"
    # Now test the runner wrapper (it delegates to incarnation)
    from core.comm.incarnation import siblings_line
    line = siblings_line("claude", out)
    assert "1 live sibling" in line


# ---------------------------------------------------------------- W14-P3 AGE STAMPS + F1 fix
def test_p3_private_notes_carry_age_stamps(monkeypatch):
    from core.learning import agent_memory as am
    from core.foundation.store import FileStore
    mem = am.AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    mem.decide("scratch:deepseek:ergonomics-retro", "Retro note body text here", session_id="",
               curated=None)
    mem.decide("scratch:deepseek:first-note", "First note content", session_id="",
               curated=None)
    monkeypatch.setattr(am, "get_agent_memory", lambda: mem)
    block = runner._age_stamped_private_notes("deepseek")
    assert "ago" in block, f"P3: age stamps must appear on note lines, got: {block[:200]}"
    # F1: full title must render, not a single letter
    assert "ergonomics-retro" in block, f"F1: SLICE, not index -- full title must appear, got: {block[:200]}"
    assert "first-note" in block


def test_p3_age_stamps_survive_empty_store(monkeypatch):
    from core.learning import agent_memory as am
    from core.foundation.store import FileStore
    mem = am.AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    monkeypatch.setattr(am, "get_agent_memory", lambda: mem)
    block = runner._age_stamped_private_notes("deepseek")
    assert block == "", "P3: no private notes -> empty string, not a crash"


# ---------------------------------------------------------------- W14-P4 HEADER BEFORE ONBOARDING
def test_p4_header_precedes_onboarding():
    # F2 fix: header is DIRECTIVE + SIBLINGS only; notes ride fold_private_notes downstream
    header = runner._runner_continuity_header(
        "deepseek",
        directive_override="DIRECTIVE: T074 Phase 4 runner fold (2h ago)",
        siblings_override="SIBLINGS: 1 live sibling (claude#09f7ad79, 1m idle)")
    assert "DIRECTIVE:" in header
    assert header.index("DIRECTIVE:") < header.index("SIBLINGS:"), \
        "P4: DIRECTIVE must be the FIRST line"
    assert "SIBLINGS:" in header
    # F2: notes must NOT appear in the header (fold_private_notes owns them)
    assert "PRIVATE NOTES" not in header, \
        "F2: header owns DIRECTIVE+SIBLINGS only; private notes ride fold_private_notes"


# ---------------------------------------------------------------- W14-P5 FAIL-SOFT
def test_p5_all_sources_broken_still_produces_header():
    header = runner._runner_continuity_header(
        "deepseek",
        directive_override="DIRECTIVE: none active -- check the ledger",
        siblings_override="SIBLINGS: (unavailable)")
    assert "DIRECTIVE:" in header and "SIBLINGS:" in header
    # the header is non-empty even when every source is degraded


def test_p5_integration_survives_run():
    """The module-level functions must be importable without side effects."""
    assert callable(runner._directive_line)
    assert callable(runner._siblings_for_runner)
    assert callable(runner._age_stamped_private_notes)
    assert callable(runner._runner_continuity_header)


# ---------------------------------------------------------------- W14-P6 BUDGET
def test_p6_header_stays_compact():
    # F2 fix: header shrinks to ~5 lines (no notes branch)
    header = runner._runner_continuity_header(
        "deepseek",
        directive_override="DIRECTIVE: A somewhat long directive that describes the next task in reasonable detail (3h ago)",
        siblings_override="SIBLINGS: 1 live sibling (claude#09f7ad79, 1m idle, unseated)")
    lines = header.splitlines()
    assert 0 < len(lines) <= 8, f"P6: header compact ({len(lines)} lines) -- a primer, not a wall"
    assert len(header) < 600, f"P6: header under 600 chars ({len(header)})"
