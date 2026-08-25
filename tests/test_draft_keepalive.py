"""Pins for the auto-handoff keepalive — the draft must survive an ungraceful death.

2026-08-24. `chronicles/last-session-draft.md` is the auto-handoff, written by the
SessionEnd/PreCompact hook. Both are GRACEFUL exits. At 12:01:59 the conductor's GPU
process crashed; neither hook fired; no draft was written. The file on disk afterwards is
stamped 14:46:12 — from a session that ended cleanly after the recovery. The seats that
reconstructed the outage did it from raw logs.

The safety net was attached to the happy path, which is this day's recurring shape.

These pins govern the throttle decision and the never-raise contract. The trigger is NOT
wired yet, deliberately: the natural one is the Stop hook, which runs on every turn of
every claude session, so a defect there wedges the fleet rather than a seat.
"""
from __future__ import annotations

import pytest

from agent.harness import draft_keepalive as dk

P = r"C:\repo\chronicles\last-session-draft.md"


def _probe(*, present=True, age=0.0, now=1000.0):
    return dict(exists=lambda p: present, getmtime=lambda p: now - age)


# --------------------------------------------------- the throttle, both directions
def test_a_fresh_draft_is_left_alone_so_the_hot_path_stays_nearly_free():
    """The common case must be one stat() and an early return. This hook would run on
    every turn of every seat; real work there is not free."""
    assert dk.should_refresh(P, now=1000.0, max_age=600.0,
                             **_probe(age=30.0)) is False


def test_a_stale_draft_is_rewritten():
    assert dk.should_refresh(P, now=1000.0, max_age=600.0,
                             **_probe(age=900.0)) is True


def test_the_boundary_is_inclusive_so_a_draft_cannot_sit_exactly_at_the_limit_forever():
    assert dk.should_refresh(P, now=1000.0, max_age=600.0,
                             **_probe(age=600.0)) is True


# ------------------------------------------- missing and unreadable FAIL TOWARD WRITING
def test_a_MISSING_draft_counts_as_stale_not_as_nothing_to_do():
    """THE case this module exists for. A missing draft is what a crashed session leaves
    behind; it is the worst state, not a reason to skip."""
    assert dk.should_refresh(P, now=1000.0, max_age=600.0,
                             **_probe(present=False)) is True


def test_an_unreadable_mtime_counts_as_stale():
    """Fail toward writing: an extra draft costs one file; a skipped one costs the next
    seat booting blind."""
    def boom(_p):
        raise OSError("mtime unreadable")
    assert dk.should_refresh(P, now=1000.0, max_age=600.0,
                             exists=lambda p: True, getmtime=boom) is True


# ------------------------------------------------------------------ the kill switch
def test_the_kill_switch_stops_it_dead(monkeypatch):
    monkeypatch.setenv(dk.ENV_OFF, "0")
    assert dk.should_refresh(P, now=1000.0, max_age=600.0, **_probe(present=False)) is False
    out = dk.refresh(P, write=lambda: pytest.fail("must not write when disabled"))
    assert out["wrote"] is False and "disabled" in out["reason"]


def test_a_bad_max_age_env_falls_back_rather_than_crashing(monkeypatch):
    monkeypatch.setenv(dk.ENV_MAX_AGE, "not-a-number")
    assert dk.max_age_s() == dk.DEFAULT_MAX_AGE_S
    monkeypatch.setenv(dk.ENV_MAX_AGE, "-5")
    assert dk.max_age_s() == dk.DEFAULT_MAX_AGE_S


# ----------------------------------------------- NEVER RAISE (the fleet-wide contract)
def test_a_writer_that_explodes_does_not_escape_into_the_turn():
    """A keepalive that can raise into a hook is worse than no keepalive: it would wedge
    every seat in the fleet to protect against one seat's crash."""
    def boom():
        raise RuntimeError("draft builder exploded")
    out = dk.refresh(P, write=boom, now=1000.0, max_age=600.0, **_probe(present=False))
    assert out["wrote"] is False
    assert "RuntimeError" in out["reason"] and "exploded" in out["reason"]


def test_the_failure_reason_carries_the_MESSAGE_not_just_the_class():
    """The conductor gate logged only the exception type all day, so a real probe failure
    and a drill's fake one rendered identically. Not repeating that here."""
    def boom():
        raise ValueError("ledger unreachable")
    out = dk.refresh(P, write=boom, now=1000.0, max_age=600.0, **_probe(present=False))
    assert "ledger unreachable" in out["reason"], out


# ------------------------------------------------------- a skip is a STATED decision
def test_every_outcome_states_its_reason():
    """A silent skip and a silent success are the same observation — the exact ambiguity
    that made the gate's 2h44m of quiet unreadable. Every path returns words."""
    wrote = dk.refresh(P, write=lambda: None, now=1000.0, max_age=600.0,
                       **_probe(present=False))
    skipped = dk.refresh(P, write=lambda: pytest.fail("fresh draft must not be rewritten"),
                         now=1000.0, max_age=600.0, **_probe(age=5.0))
    assert wrote["wrote"] is True and wrote["reason"]
    assert skipped["wrote"] is False and skipped["reason"]
    assert wrote["reason"] != skipped["reason"]


def test_the_writer_is_INJECTED_so_this_module_owns_no_second_way_to_build_a_draft():
    """There must be exactly one draft builder in the house. This module throttles the
    existing one; it does not grow a rival."""
    import inspect
    src = inspect.getsource(dk)
    # Check for a CALL, not a MENTION. The first version of this pin grepped the bare
    # name and fired on the module's own docstring, which names the builder it delegates
    # to — a token-level check that cannot tell prose from code, which is the same trap
    # the spawn closing-report had to strip harness tracebacks around.
    assert "write_last_session_draft(" not in src, \
        "the keepalive must delegate to the one existing builder, not reimplement it"
    assert "import agent_cli" not in src, \
        "the keepalive must not reach for the builder itself; the caller injects it"
    calls = []
    dk.refresh(P, write=lambda: calls.append(1), now=1000.0, max_age=600.0,
               **_probe(present=False))
    assert calls == [1]


# --------------------------------------------------- wiring is deliberately absent
def test_the_keepalive_is_NOT_wired_into_the_stop_hook_yet():
    """Recorded as a DECISION rather than an omission. The Stop hook runs on every turn
    of every claude session; a defect there wedges the whole fleet at once. Wiring is a
    separate slice for a seat with room to think — the same discipline the conductor gate
    used (built 3431118a, wired 5c09bb5a).

    When it IS wired, this pin flips to assert the call site exists."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    hook = root / "scripts" / "hooks" / "claude_stop.py"
    if not hook.is_file():
        pytest.skip("stop hook not present in this tree")
    assert "draft_keepalive" not in hook.read_text(encoding="utf-8"), \
        ("the keepalive is now wired — good; flip this pin to assert the call site and "
         "record the drill that proved a hard-killed seat leaves a draft")
