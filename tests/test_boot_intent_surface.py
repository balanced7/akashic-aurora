"""
Boot-intent gap fixes (2026-07-11 incident: a fresh session built UI against an
engine-first directive that boot never surfaced). Fenced dual diagnosis reconciled to
THREE fixes, deepseek's zero-new-primitive framing adopted:

  F2 -- the governing-arc picker must NEVER present a DONE arc (the incident: boot named
        comms-pillar-synthesis, whose own note body says "ARC COMPLETE, ALL SLICES
        SHIPPED", as governing).
  F1 -- boot renders the current-directive (the `next-focus` note, which already IS the
        priority note-kind) FIRST-CLASS, above the raw NEXT list, with authority.
  F4 -- `wrap --focus` captures the directive at decision time (the incident's root: the
        engine-first intent was saved 9 minutes late, after the rogue session ran).

Pre-registered per M3 (this precedes the fixes). Subprocess against the real CLI so the
whole boot-head assembly is under test. Redis-backed; skips offline.
Run: py -m pytest tests/test_boot_intent_surface.py -q
"""
import os
import subprocess
import sys
import uuid

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cli(*args):
    env = dict(os.environ)
    return subprocess.run([sys.executable, "agent_cli.py", *args], cwd=REPO,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120, env=env)


def _boot_head(agent):
    p = _cli("boot", agent, "--task", "intent-surface drill")
    if "notes store unreachable" in (p.stdout or ""):
        pytest.skip("redis not available")
    return "\n".join((p.stdout or "").splitlines()[:22])


def test_done_arc_never_governs():
    """F2: a <slug>-status note whose body declares completion must NOT be rendered as
    the governing arc -- fall through, or say 'none active', never point at a finished arc."""
    slug = f"drilldone{uuid.uuid4().hex[:6]}"
    r = _cli("note", "seeder", "--title", f"{slug}-status",
             "--note", f"GOVERNING ARC DOC: docs/{slug}-plan.md -- ARC COMPLETE 2026-07-11. "
                       "ALL SLICES SHIPPED.")
    if "[OK] noted" not in (r.stdout or ""):
        pytest.skip("redis not available")
    head = _boot_head(f"drill-{uuid.uuid4().hex[:8]}")
    # the governing-arc line must never cite the done arc as authoritative; a weak
    # fallback line that names the newest non-done note is fine, but the DONE arc is
    # skipped entirely, so it appears on NO governing-arc line.
    for line in head.splitlines():
        if line.startswith("# Governing arc:"):
            assert f"{slug}-plan.md" not in line, f"done arc leaked into: {line}"


def test_current_directive_renders_first_class():
    """F1: the next-focus note is surfaced in the boot head with authority, above NEXT."""
    marker = f"ENGINE-FIRST-{uuid.uuid4().hex[:6]}"
    r = _cli("note", "seeder", "--title", "next-focus",
             "--note", f"{marker}: do RB-23 then Wave 3 before ANY UI. UI is paused.")
    if "[OK] noted" not in (r.stdout or ""):
        pytest.skip("redis not available")
    head = _boot_head(f"drill-{uuid.uuid4().hex[:8]}")
    assert marker in head, "the current directive must be in the cold-start head"
    assert "DIRECTIVE" in head or "FOCUS" in head.upper(), \
        "rendered with authority, not as a plain note"
    # above the NEXT list: the directive line precedes the first 'next:' line
    di = next((i for i, l in enumerate(head.splitlines()) if marker in l), 99)
    ni = next((i for i, l in enumerate(head.splitlines()) if l.strip().startswith("#   next:")), 100)
    assert di < ni, "the directive is rendered ABOVE the raw NEXT list"


def test_wrap_focus_captures_intent_at_decision_time():
    """F4: `wrap --focus '...'` writes the next-focus note immediately (the root fix --
    the incident's intent was saved 9 min late)."""
    marker = f"FOCUSNOW-{uuid.uuid4().hex[:6]}"
    p = _cli("wrap", "--focus", f"{marker}: engine before UI", "--hours", "0")
    if p.returncode != 0 and "unrecognized arguments" in (p.stderr or ""):
        pytest.fail("wrap must accept --focus")
    if "redis" in (p.stderr or "").lower() and "[OK]" not in (p.stdout or ""):
        pytest.skip("redis not available")
    head = _boot_head(f"drill-{uuid.uuid4().hex[:8]}")
    assert marker in head, "wrap --focus makes the directive boot-visible immediately"
