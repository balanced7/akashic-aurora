"""
T030 L5 / RB-30 -- bus-loss stand-down + pause hygiene: pre-registered acceptance
(committed BEFORE impl, M3/T031). Spec: docs/library/design/20260701_agent-liveness-tier-stuck-lost-agent-fai_8c0d79.md L5 +
RB-30 section ("verify semantics first" -- audited 2026-07-11: provenance EXISTS in
pause()/pause_status(); MISSING = TTL on auto-pauses + a loud render at boot/sync/
doctor + the B2 dead-beat stand-down).

Contract frozen here:
  control.pause(reason, by, ttl=None) -- ttl seconds -> the pause SELF-HEALS (auto-pause
      backstops); None -> persistent (human intent stays until resumed)
  control.format_pause_line(status, now=None) -> str -- PURE render: "" when not paused;
      otherwise names by + reason + age and teaches the resume verb
  liveness.BusLossGuard(max_dead=10).beat(online) -> "ok" | "degraded" | "stand_down"
      -- consecutive offline beats degrade (with a growing, capped backoff schedule via
      .backoff_s), the max_dead-th commands stand-down; ANY online beat resets. Pure.
  wiring: boot/bifrost-sync + fleet doctor render the pause line; the runner's
      rate-limit auto-pause carries a ttl; the runner loop runs a BusLossGuard.

The LIVE fleet's global pause key is never touched here (pins patch the key name);
the kill-Redis drill runs against the sandbox instance with deepseek [verify].

Run: py -m pytest tests/test_t030_l5_busloss_pause.py -q
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.comm import control, liveness
    _BUILT = hasattr(liveness, "BusLossGuard") and hasattr(control, "format_pause_line")
except ImportError:
    control = liveness = None
    _BUILT = False

pytestmark = pytest.mark.skipif(
    not _BUILT, reason="L5 pins pre-registered; impl pending (assertions frozen)")


def _online() -> bool:
    try:
        return control._client() is not None
    except Exception:
        return False


# --- P1: a ttl'd pause self-heals; a plain pause persists (patched key, never live) ---

def test_ttl_pause_self_heals(monkeypatch):
    if not _online():
        pytest.skip("live-Redis pin; bus offline")
    # Repaired 2026-07-15: PAUSE_KEY became per-call _pause_key() in the 07-12
    # per-namespace refactor (a drill pause must never freeze the LIVE bus) and
    # this monkeypatch was missed. Isolation now rides the sanctioned ns seam.
    monkeypatch.setenv("BIFROST_NAMESPACE", "rb30pin")
    try:
        assert control.pause(reason="pin backstop", by="rb30pin", ttl=1)
        assert control.is_paused()
        time.sleep(1.3)
        assert not control.is_paused(), "auto-pause with ttl SELF-HEALS"
        assert control.pause(reason="pin manual", by="rb30pin")
        time.sleep(1.3)
        assert control.is_paused(), "ttl-less pause persists (human intent)"
    finally:
        control._client().delete("rb30pin:control:paused")


# --- P2: the pause render line is pure, loud, and teaching ---

def test_pause_line_pure_render():
    assert control.format_pause_line({"paused": False, "online": True}) == ""
    line = control.format_pause_line(
        {"paused": True, "online": True, "by": "deepseek",
         "reason": "deepseek hit reply rate limit", "ts": "2026-07-11T10:00:00"},
        now=time.mktime(time.strptime("2026-07-11T10:30:00", "%Y-%m-%dT%H:%M:%S")))
    assert "PAUSED" in line and "deepseek" in line and "rate limit" in line
    assert "30m" in line, "age computed at render (clock-free store)"
    assert "bifrost-resume" in line, "the line TEACHES the resume verb"


# --- P3: BusLossGuard -- degrade with capped growing backoff, stand down at max, reset ---

def test_bus_loss_guard_sequence():
    g = liveness.BusLossGuard(max_dead=10)
    assert g.beat(True) == "ok"
    backoffs = []
    for i in range(9):
        assert g.beat(False) == "degraded", f"beat {i + 1} degrades, never spins"
        backoffs.append(g.backoff_s)
    assert g.beat(False) == "stand_down", "the 10th consecutive dead beat exits cleanly"
    assert backoffs == sorted(backoffs), "backoff never shrinks while dead"
    assert backoffs[0] >= 1 and backoffs[-1] <= 30, "bounded: no busy-spin, no coma"
    g2 = liveness.BusLossGuard(max_dead=10)
    for _ in range(5):
        g2.beat(False)
    assert g2.beat(True) == "ok" and g2.dead_beats == 0, "one live beat resets fully"


# --- P4: the doors render the pause line (built != wired) ---

def test_pause_line_wired_to_render_paths():
    pull = open(os.path.join(_ROOT, "agent", "bifrost_pull.py"), encoding="utf-8").read()
    doctor = open(os.path.join(_ROOT, "core", "comm", "doctor.py"), encoding="utf-8").read()
    assert "format_pause_line" in pull, "boot/bifrost-sync surface a leftover freeze"
    assert "format_pause_line" in doctor, "fleet doctor surfaces a leftover freeze"


# --- P5: the runner wires both halves (ttl'd auto-pause + the guard) ---

def test_runner_wired():
    src = open(os.path.join(_ROOT, "scripts", "bifrost_runner_deepseek.py"),
               encoding="utf-8").read()
    assert "BusLossGuard" in src, "the runner loop runs the dead-beat guard"
    lines = src.splitlines()
    idx = next(i for i, l in enumerate(lines) if "hit reply rate limit" in l)
    stmt = " ".join(lines[max(0, idx - 1): idx + 2])
    assert "ttl=" in stmt, "the rate-limit auto-pause carries a ttl (self-healing backstop)"
