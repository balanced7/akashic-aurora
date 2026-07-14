"""
A1 -- targeted halt on the Bifrost control plane (core/comm/control.py).

Bar: halt() can freeze ONE agent while the others keep running, resume is selective, and the
all-agents case still rides the existing global pause flag (backward-compatible per DeepSeek's note).

Redis-backed: uses the real Redis but ISOLATES itself by pointing BIFROST_NAMESPACE at a throwaway
namespace -- control resolves its keys PER-CALL from that env var (like Bus.ns, since the 2026-07-12
namespace-scope fix), so the test never touches the live bus's control keys (which would otherwise
freeze a running runner). Skips if Redis is down. Run: py -m pytest tests/test_bifrost_control_halt.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import control


@pytest.fixture
def ns(monkeypatch):
    """Route control's per-call key resolution to a throwaway namespace + clean it up. Skips if Redis is down."""
    c = control._client()
    if c is None:
        pytest.skip("redis not available")
    n = f"bifrost_test_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", n)
    yield n
    keys = c.keys(f"{n}:*")
    if keys:
        c.delete(*keys)


# --------------------------------------------------------------- the A1 slice bar
def test_halt_one_agent_others_untouched(ns):
    """Halt a single agent; only that agent reads as halted."""
    assert control.halt(targets=["deepseek"]) is True
    assert control.is_halted("deepseek") is True
    assert control.is_halted("claude") is False          # others untouched
    assert control.is_paused() is False                   # no global pause set


def test_resume_selected(ns):
    """Resume just the halted agent; leaves any other targeted halt in place."""
    control.halt(targets=["deepseek", "claude"])
    assert control.is_halted("deepseek") and control.is_halted("claude")
    assert control.resume(targets=["deepseek"]) is True
    assert control.is_halted("deepseek") is False
    assert control.is_halted("claude") is True            # the un-named one stays frozen


# --------------------------------------------------------------- halt-all reuses the global pause
def test_halt_all_rides_global_pause(ns):
    """targets=None -> the existing global pause flag (backward compat), freezing everyone."""
    assert control.halt() is True
    assert control.is_paused() is True                    # it's the SAME flag, not N per-agent keys
    assert control.is_halted("deepseek") is True
    assert control.is_halted("anyone-at-all") is True
    assert control.halted_agents() == {}                  # global pause is not a per-agent halt


def test_resume_all_clears_global_and_targeted(ns):
    """resume() with no targets wipes the global pause AND every per-agent halt."""
    control.halt()                       # global
    control.halt(targets=["deepseek"])   # + targeted
    assert control.resume() is True
    assert control.is_paused() is False
    assert control.is_halted("deepseek") is False
    assert control.halted_agents() == {}


# --------------------------------------------------------------- introspection + provenance
def test_halted_agents_reports_targeted_with_reason(ns):
    control.halt(targets=["deepseek"], reason="stalled at tool boundary", by="claude")
    agents = control.halted_agents()
    assert set(agents) == {"deepseek"}
    assert agents["deepseek"]["reason"] == "stalled at tool boundary"
    assert agents["deepseek"]["by"] == "claude"


def test_norm_targets_accepts_str_and_filters_blanks(ns):
    control.halt(targets="deepseek")                      # bare string -> single target
    assert control.is_halted("deepseek") is True
    assert control.halt(targets=["", "   "]) is True      # all-blank normalizes to [] == halt-all
    assert control.is_paused() is True


# --------------------------------------------------------------- backward compat + fail-open
def test_noarg_resume_still_clears_pause(ns):
    """Existing callers do control.pause() / control.resume() -- must keep working unchanged."""
    control.pause(reason="human barge-in")
    assert control.is_paused() is True
    assert control.resume() is True
    assert control.is_paused() is False


def test_fail_open_when_offline(monkeypatch):
    """Bus offline -> writes return False, reads say 'not halted' (never wedge the bus)."""
    monkeypatch.setattr(control, "_client", lambda: None)
    assert control.halt(targets=["deepseek"]) is False
    assert control.resume(targets=["deepseek"]) is False
    assert control.is_halted("deepseek") is False
    assert control.halted_agents() == {}
