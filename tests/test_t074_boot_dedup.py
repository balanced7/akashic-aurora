"""T074 Phase 4 (claude side) pins -- W13 boot dedup: a PRIMER-AWARE boot stops
duplicating whisper-carried sections (deepseek spec, "First-boot sections": REMOVE
where-we-are one-liner/funnel/draft/delta/mail from the boot; ADD the full
where-we-are body + sibling details to the head; KEEP map/method/arc/precedence/
ledger/DECISIONS/NOTES).

BUILD REFINEMENTS (flagged, T073 precedent):
  R13  The dedup predicate is SESSION PRESENCE (runner_lock.session_holder_token()):
       a harness session got the whisper; a bare terminal or a runner did not and
       keeps the legacy full boot. AKASHIC_BOOT_FULL=1 forces legacy from inside a
       session (the debugging hatch).
  R14  Under primer-aware boot the UNREAD BIFROST peek block is skipped with the rest
       (the whisper carries the count; presence rides SIBLINGS now); the LOCKS block
       stays (locks are not whisper-carried).
  R15  Skipping the DELTA render also skips the mark-advance (the mark-lag contract:
       a mark moves only when content was DELIVERED). Side effect: T062's
       self-defeating pointer is fixed on the primer path -- `delta <agent>` stays
       addressable after boot.
  R16  The NOTES section skips its where-we-are entry under primer-aware boot (the
       head now carries the FULL body -- in-boot duplication is the same disease as
       whisper/boot duplication).
"""
import os
import subprocess
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from core.learning import agent_memory as am
from core.foundation.store import FileStore

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fake_mem(monkeypatch, wwa_chars=500):
    import tempfile
    mem = am.AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    mem.decide("where-we-are", "RESUME ANCHOR " + ("x" * wwa_chars), curated=True)
    mem.decide("next-focus", "the directive")
    monkeypatch.setattr(am, "get_agent_memory", lambda: mem)
    return mem


# ---------------------------------------------------------------- W13 head upgrade (unit)
def test_w13_primer_aware_head_carries_full_where_we_are(monkeypatch):
    _fake_mem(monkeypatch, wwa_chars=500)
    head = agent_cli._orientation_header("claude", primer_aware=True)
    wwa_lines = [l for l in head.splitlines() if "where-we-are" in l.lower()]
    assert wwa_lines, "head must still carry where-we-are"
    assert sum(len(l) for l in wwa_lines) > 300, \
        "W13: primer-aware head carries the FULL body (resume anchor), not the 120-clip"


def test_w13_legacy_head_keeps_the_one_liner(monkeypatch):
    _fake_mem(monkeypatch, wwa_chars=500)
    head = agent_cli._orientation_header("claude", primer_aware=False)
    wwa_lines = [l for l in head.splitlines() if l.startswith("# where-we-are:")]
    assert wwa_lines and len(wwa_lines[0]) < 160, "legacy boot keeps the compact one-liner"


def test_w13_primer_aware_head_names_siblings(monkeypatch):
    _fake_mem(monkeypatch)
    monkeypatch.setattr(agent_cli, "_boot_siblings_line",
                        lambda agent_id: "# siblings: claude#b0b7771d (idle 45m, claims: T068)")
    head = agent_cli._orientation_header("claude", primer_aware=True)
    assert "siblings:" in head, "W13: sibling details join the primer-aware head"


def test_w13_own_session_is_not_its_own_sibling(monkeypatch):
    """Live-drill defect 2026-07-15: the first W13 boot rendered the CALLER's session as
    its own sibling. _boot_siblings_line must pass the caller's sid as my_session."""
    seen = {}

    def fake_live(agent_id, my_session=None):
        seen["my_session"] = my_session
        return []

    import core.comm.incarnation as inc
    monkeypatch.setattr(inc, "live_incarnations", fake_live)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "self-sid-1234")
    agent_cli._boot_siblings_line("claude")
    assert seen.get("my_session") == "self-sid-1234", \
        "the caller's own incarnation must be excluded from its sibling line"


# ---------------------------------------------------------------- W13 section skips (integration)
def _boot(env_extra):
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("CLAUDE_SESSION_ID", None)
    env.pop("AKASHIC_BOOT_FULL", None)
    env["_AISETUP_TEST_ISOLATED"] = "1"
    env.update(env_extra)
    out = subprocess.run([sys.executable, "agent_cli.py", "boot", "w13-probe"],
                        capture_output=True, text=True, timeout=120, cwd=_REPO, env=env)
    return out.stdout


def test_w13_session_boot_skips_whisper_sections():
    out = _boot({"CLAUDE_CODE_SESSION_ID": "w13-test-session"})
    for gone in ("## FUNNEL", "## LAST-SESSION DRAFT", "## DELTA", "## UNREAD BIFROST"):
        assert gone not in out, f"W13: primer-aware boot must not duplicate {gone}"
    assert "primer-aware" in out, "the dedup must be SAID, not silent (packet law)"


_WHISPER_COVERED = ("## FUNNEL", "## LAST-SESSION DRAFT", "## DELTA", "## UNREAD BIFROST")


def test_w13_bare_terminal_keeps_full_boot():
    out = _boot({})
    assert "primer-aware" not in out, "R13: no session -> no whisper existed -> full boot"
    # each section is individually fail-open (its data source may be down in the
    # isolated env -- a T070-class flake caught 2026-07-15); ANY of them rendering
    # proves the guards did not fire
    assert any(s in out for s in _WHISPER_COVERED), \
        f"legacy boot rendered NONE of the whisper-covered sections: {out[:400]}"


def test_w13_boot_full_hatch_forces_legacy():
    out = _boot({"CLAUDE_CODE_SESSION_ID": "w13-test-session", "AKASHIC_BOOT_FULL": "1"})
    assert "primer-aware" not in out, "R13: the hatch restores the legacy full boot"
    assert any(s in out for s in _WHISPER_COVERED)
