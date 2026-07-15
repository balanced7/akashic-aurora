"""T074 Phase 1 pins -- whisper v2: the SessionStart whisper BECOMES the primer.

PRE-REGISTERED acceptance for pins W1-W6 of the reconciled build spec
(research/reviewed/t074-continuity-reconciliation-2026-07-15.md; deepseek's half
research/reviewed/deepseek-t074-continuity-design-2026-07-15.md GOVERNS).

Section order (recon contract): DIRECTIVE > WHERE (age+curated) > SIBLINGS > DELTA >
THEMES > MAIL > DRAFT > FUNNEL > BOOT (+STORY in spill). Drop order bottom-up;
DIRECTIVE/WHERE/SIBLINGS are the orienting core and drop last.

BUILD REFINEMENTS (flagged per the T073 pre-registration precedent):
  R1  A note with NO curated flag renders age-only (neither `curated` nor `auto` token):
      the flag beats inference (recon note 1), and inference-free means legacy notes
      never CLAIM a provenance they can't prove.
  R2  THEMES renders only when the session-themes note is < 30 days old (recon note 2).
  R3  STORY: one spill line naming the latest dated JOURNEY.md entry (recon note 3);
      renders only when the budget has room AFTER all surviving sections.
  R4  SIBLINGS v1 reads the EXISTING signals (wake_seat activity markers + seat files)
      via core/comm/incarnation.live_incarnations(); Phase 3 upgrades the same seam to
      TTL cards (spec sec. 4 precedent: "the runner lock IS the incarnation card").
  R5  The v1 whisper tests in test_sessionstart_autoboot.py keep the TIERING contract
      (repo/home/elsewhere, kill switch, fail-soft) -- their v1 SHAPE assertions
      (notes: line, <=10 lines) are superseded by this spec and updated in the build
      commit, never silently.
  R6  The line budget is env-tunable (AKASHIC_WHISPER_LINES, default 12) so the drop
      order is TESTABLE (the 9 sections structurally max out at 11 lines + spill).
"""
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.harness import context as ctx
from agent.harness.scope import repo_root
from core.learning.agent_memory import AgentMemory, Decision
from core.foundation.store import FileStore

_REPO = repo_root()


def _dec(title, body, hours_ago=2.0, curated=None):
    """A real Decision (the dataclass change is itself under pin) aged `hours_ago`."""
    created = (datetime.now() - timedelta(hours=hours_ago)).isoformat()
    return Decision(id=f"ADR_test_{title}", title=title, status="accepted", context="",
                    decision=body, rationale=[], alternatives=[],
                    consequences={"positive": [], "negative": []},
                    created_at=created, curated=curated)


def _wire(monkeypatch, notes=None, siblings=None, unread=0, draft=False, delta=0,
          funnel="funnel: 91 lessons | value 4.3%", journey="The night the contract carried strangers (2026-07-14/15)"):
    monkeypatch.setattr(ctx, "_fetch_notes", lambda: list(notes or []))
    monkeypatch.setattr(ctx, "_live_siblings", lambda agent_id, my_session="": list(siblings or []))
    monkeypatch.setattr(ctx, "_unread_count", lambda agent_id: unread)
    monkeypatch.setattr(ctx, "_draft_fresh", lambda: draft)
    monkeypatch.setattr(ctx, "_delta_count", lambda agent_id: delta)
    monkeypatch.setattr(ctx, "_funnel_line", lambda: funnel)
    monkeypatch.setattr(ctx, "_journey_latest", lambda: journey)


def _full(monkeypatch, **over):
    base = dict(
        notes=[_dec("next-focus", "T074 Phase 1 whisper v2", hours_ago=3),
               _dec("where-we-are", "SESSION HANDOFF: epic night closes; T074 next. " * 8,
                    hours_ago=2, curated=True),
               _dec("session-themes", "THE HARD-TO-PIN THEMES: gauge inversion; harness tier beats model tier.",
                    hours_ago=10)],
        siblings=[{"session_id": "b0b7771d-9c2a-4f00-8888-000000000000", "age_min": 45.0, "has_seat": True}],
        unread=3, draft=True, delta=4)
    base.update(over)
    _wire(monkeypatch, **base)
    return ctx.build_autoboot_context(_REPO, "claude", session_id="09f7ad79-3749-4c5e-a860-9d9e05133eaa")


# ---------------------------------------------------------------- W1 DIRECTIVE
def test_w1_directive_is_the_first_line(monkeypatch):
    out = _full(monkeypatch)
    first = out.splitlines()[0]
    assert first.startswith("[akashic] DIRECTIVE:"), f"W1: first line must be the DIRECTIVE, got: {first}"
    assert "T074 Phase 1" in first


def test_w1_no_next_focus_teaches_the_ledger(monkeypatch):
    out = _full(monkeypatch, notes=[_dec("where-we-are", "state", curated=True)])
    first = out.splitlines()[0]
    assert first.startswith("[akashic] DIRECTIVE:")
    assert "ledger" in first.lower(), "W1 fallback: no directive -> point at the task ledger"


# ---------------------------------------------------------------- W2 WHERE + curated flag
def test_w2_where_carries_age_and_curated_flag(monkeypatch):
    out = _full(monkeypatch)
    where = next(l for l in out.splitlines() if "WHERE:" in l)
    assert "curated" in where and "h ago" in where, f"W2: expected '(curated, Nh ago)', got: {where}"


def test_w2_mechanical_note_renders_auto(monkeypatch):
    out = _full(monkeypatch, notes=[_dec("where-we-are", "auto-distilled state", hours_ago=2, curated=False)])
    where = next(l for l in out.splitlines() if "WHERE:" in l)
    assert "auto" in where and "curated" not in where


def test_w2_refinement_r1_legacy_note_renders_age_only(monkeypatch):
    out = _full(monkeypatch, notes=[_dec("where-we-are", "legacy pre-flag note", hours_ago=2, curated=None)])
    where = next(l for l in out.splitlines() if "WHERE:" in l)
    assert "h ago" in where
    assert "curated" not in where and "auto" not in where, \
        "R1: an absent flag must not be inferred either way"


# ---------------------------------------------------------------- W3 SIBLINGS
def test_w3_solo_when_no_siblings(monkeypatch):
    out = _full(monkeypatch, siblings=[])
    sib = next(l for l in out.splitlines() if "SIBLINGS:" in l)
    assert "solo" in sib


def test_w3_sibling_line_names_the_incarnation(monkeypatch):
    out = _full(monkeypatch)
    sib = next(l for l in out.splitlines() if "SIBLINGS:" in l)
    assert "1 live sibling" in sib and "claude#b0b7771d" in sib and "45m idle" in sib


# ---------------------------------------------------------------- W4 age stamps live-vs-note
def test_w4_note_lines_stamped_live_lines_not(monkeypatch):
    out = _full(monkeypatch)
    lines = out.splitlines()
    for probe in ("DIRECTIVE:", "WHERE:", "THEMES:"):
        l = next(x for x in lines if probe in x)
        assert "ago" in l, f"W4: note-derived line lacks an age stamp: {l}"
    for probe in ("mail:", "delta:", "SIBLINGS:"):
        l = next(x for x in lines if probe in x)
        assert "ago" not in l, f"W4: live line must NOT carry an age stamp: {l}"


# ---------------------------------------------------------------- W5 staleness
def test_w5_stale_note_gains_stale_prefix(monkeypatch):
    out = _full(monkeypatch,
                notes=[_dec("next-focus", "old directive", hours_ago=12 * 24),
                       _dec("where-we-are", "old state", hours_ago=12 * 24, curated=True)])
    lines = out.splitlines()
    assert any("[STALE]" in l and "DIRECTIVE:" in l for l in lines), "W5: 12d-old directive must be [STALE]"
    assert any("[STALE]" in l and "WHERE:" in l for l in lines)


def test_w5_fresh_note_is_not_stale(monkeypatch):
    out = _full(monkeypatch)
    assert "[STALE]" not in out


# ---------------------------------------------------------------- W6 budget + drop order
def test_w6_full_whisper_fits_twelve_lines(monkeypatch):
    out = _full(monkeypatch)
    assert 0 < len(out.splitlines()) <= 12, f"W6: {len(out.splitlines())} lines"


def test_w6_drop_order_protects_the_orienting_core(monkeypatch):
    monkeypatch.setenv("AKASHIC_WHISPER_LINES", "6")
    out = _full(monkeypatch)
    lines = out.splitlines()
    assert len(lines) <= 6
    joined = "\n".join(lines)
    for core in ("DIRECTIVE:", "WHERE:", "SIBLINGS:"):
        assert core in joined, f"drop order must protect {core}"
    assert "funnel:" not in joined and "boot " not in joined.lower().replace("[akashic]", ""), \
        "R6: BOOT and FUNNEL drop first under budget pressure"


# ---------------------------------------------------------------- R2 THEMES window
def test_r2_themes_line_renders_fresh_and_absent_when_old(monkeypatch):
    out = _full(monkeypatch)
    assert any("THEMES:" in l for l in out.splitlines())
    out2 = _full(monkeypatch,
                 notes=[_dec("next-focus", "x", 3),
                        _dec("where-we-are", "y", 2, curated=True),
                        _dec("session-themes", "old themes", hours_ago=35 * 24)])
    assert not any("THEMES:" in l for l in out2.splitlines()), "R2: themes >30d old stay off the whisper"


# ---------------------------------------------------------------- R3 STORY spill
def test_r3_story_spill_line_when_room(monkeypatch):
    out = _full(monkeypatch, unread=0, draft=False, delta=0)
    assert any("STORY:" in l and "JOURNEY" in l for l in out.splitlines()), \
        "R3: quiet whisper has room -> the story pointer rides the spill"


def test_r3_story_yields_under_budget_pressure(monkeypatch):
    monkeypatch.setenv("AKASHIC_WHISPER_LINES", "6")
    out = _full(monkeypatch)
    assert not any("STORY:" in l for l in out.splitlines())


# ---------------------------------------------------------------- curated flag round-trip
def test_curated_flag_round_trips_through_the_store():
    mem = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    mem.decide("where-we-are", "hand-written handoff", curated=True)
    d = next(x for x in mem.get_decisions(days=1) if x.title == "where-we-are")
    assert d.curated is True
    mem2 = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m2.json")))
    mem2.decide("where-we-are", "wrap distillation", curated=False)
    d2 = next(x for x in mem2.get_decisions(days=1) if x.title == "where-we-are")
    assert d2.curated is False


def test_curated_default_none_and_legacy_records_load():
    mem = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    mem.decide("open-question", "no flag passed")
    d = next(x for x in mem.get_decisions(days=1) if x.title == "open-question")
    assert d.curated is None, "unflagged writes stay flag-free (R1: no inference)"


# ---------------------------------------------------------------- R4 live_incarnations v1
def _touch_marker(tmp, agent, sid, age_s=0.0):
    p = os.path.join(tmp, f"bifrost_wake_{agent}_{sid}.alive")
    with open(p, "w") as f:
        f.write(str(time.time() - age_s))
    return p


def test_r4_fresh_marker_is_a_live_incarnation(tmp_path):
    from core.comm.incarnation import live_incarnations
    tmp = str(tmp_path)
    _touch_marker(tmp, "claude", "aaaabbbb-1111-2222-3333-444455556666", age_s=60)
    out = live_incarnations("claude", tmp=tmp)
    assert len(out) == 1
    assert out[0]["session_id"].startswith("aaaabbbb")
    assert out[0]["age_min"] < 2.0
    assert out[0]["has_seat"] is False


def test_r4_stale_marker_and_own_session_are_excluded(tmp_path):
    from core.comm.incarnation import live_incarnations
    tmp = str(tmp_path)
    _touch_marker(tmp, "claude", "aaaabbbb-1111-2222-3333-444455556666", age_s=3 * 3600)
    _touch_marker(tmp, "claude", "09f7ad79-0000-0000-0000-000000000000", age_s=10)
    out = live_incarnations("claude", my_session="09f7ad79-0000-0000-0000-000000000000", tmp=tmp)
    assert out == [], "stale markers and the caller's own session never count as siblings"


def test_r4_seat_file_reported(tmp_path):
    from core.comm.incarnation import live_incarnations
    tmp = str(tmp_path)
    sid = "ccccdddd-1111-2222-3333-444455556666"
    _touch_marker(tmp, "claude", sid, age_s=30)
    with open(os.path.join(tmp, f"bifrost_wake_claude_{sid}.pid"), "w") as f:
        f.write("12345")
    out = live_incarnations("claude", tmp=tmp)
    assert out and out[0]["has_seat"] is True


def test_r4_foreign_agent_markers_never_leak(tmp_path):
    from core.comm.incarnation import live_incarnations
    tmp = str(tmp_path)
    _touch_marker(tmp, "claude-2", "eeeeffff-1111-2222-3333-444455556666", age_s=30)
    assert live_incarnations("claude", tmp=tmp) == [], \
        "prefix-exact: agent 'claude' never enumerates 'claude-2' incarnations (wake_seat precedent)"
