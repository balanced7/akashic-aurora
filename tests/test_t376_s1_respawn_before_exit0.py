"""T376-S1 PRE-REGISTERED ACCEPTANCE — respawn-before-exit-0 contract + jitter.

Cites fences/t376-metabolism/reconciliation.md (the ratified build spec) rule 2
and build slice S1:

  S1 daemon: pin the respawn-before-exit-0 contract (N1 earned signal) + jitter.

THE CONTRACT (N1, Navi's find — the exit code is the earned signal):
  0 = my successor exists (respawn_self already succeeded). The daemon's
      breaker stands down (N1 already coded: _handle_exit code==0 -> never
      auto-respawn, _next_spawn_at=inf).
  nonzero = count me, respawn me (crash).
  failed respawn = NO EXIT AT ALL, keep running (self_restart's existing law).

The only code path that may exit 0 on a rotation is the one that already
launched a successor. This is make-before-break generalized to every organ.

THE JITTER (reconciliation rule 2, last sentence): per-organ jitter
`hash(organ) % 120s` survives for fleet-blackout smoothing only — spread the
rotation so a busy repo doesn't rotate all three organs in the same instant
and black the fleet. The tree's own law (control_channel.py:66) forbids
Python's builtin hash() for a cross-process agreement: it is randomised per
process (PYTHONHASHSEED), so two processes would disagree about the same
organ's delay. The deterministic form is crc32(organ) — the same primitive
port_for() already uses.

RED-first (M3): the jitter helper does not exist yet; the respawn-before-exit-0
law is coded but UNPINNED (regression-open). These pins lock both. Commit RED,
then implement.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import self_restart as SR


# ------------------------------------------------------------------ S1-P1
def test_s1_p1_rotation_jitter_is_deterministic_and_in_band():
    """Per-organ jitter: deterministic (same organ -> same delay across
    processes), bounded [0, 120s), and a pure function of the organ name.

    Determinism is the WHOLE point: fleet-blackout smoothing requires every
    process computing the same organ's delay to AGREE, or the smoothing is a
    per-process coin-flip and the fleet still flaps together.
    """
    assert hasattr(SR, "rotation_jitter_s"), \
        "S1: self_restart.rotation_jitter_s(organ) does not exist yet (RED)"

    # same organ -> same delay (determinism; no PYTHONHASHSEED dependence)
    a1 = SR.rotation_jitter_s("daemon")
    a2 = SR.rotation_jitter_s("daemon")
    assert a1 == a2, f"jitter must be deterministic per organ: {a1} != {a2}"

    # bounded and non-negative
    for organ in ("daemon", "gateway", "ui", "runner", "anything-at-all"):
        d = SR.rotation_jitter_s(organ)
        assert isinstance(d, (int, float)) and d >= 0.0 and d < 120.0, \
            f"jitter for {organ!r} out of band [0,120): {d!r}"

    # pure function of the NAME: distinct organs may (probabilistically) differ,
    # but two DIFFERENT names must never be forced equal by a broken impl that
    # ignores its argument — pin the arg actually matters.
    assert SR.rotation_jitter_s("daemon") == SR.rotation_jitter_s("daemon")


def test_s1_p2_jitter_uses_crc32_not_python_hash():
    """The tree's own law: Python's hash() is randomised per process
    (control_channel.py:66). Jitter must NOT ride builtin hash(), or two
    processes disagree about the same organ's delay and the smoothing dies.

    Pin the PRIMITIVE at the source: the helper must use zlib.crc32 (the same
    deterministic primitive port_for() documents), and must never call the
    builtin hash() on the organ name. Source-level pin because a runtime hash()
    trap would break pytest's own bytecode cache (pathlib hashes).
    """
    import inspect
    import zlib
    src = inspect.getsource(SR.rotation_jitter_s)
    assert "crc32" in src, \
        "S1: rotation_jitter_s must use zlib.crc32 (deterministic), matching " \
        f"control_channel.port_for's law. Source:\n{src}"
    # No bare hash( call on anything — the randomised-builtin trap.
    assert "hash(" not in src, \
        f"S1: rotation_jitter_s must not call the randomised builtin hash(). " \
        f"Source:\n{src}"


# ------------------------------------------------------------------ S1-P3
def test_s1_p3_failed_respawn_never_advances_to_exit0(monkeypatch):
    """The earned signal is non-negotiable: a rotation may exit 0 ONLY after a
    successor was actually launched. If respawn_self fails (returns False), the
    caller that trusts maybe_self_restart's return value gets None -> it keeps
    running. This pin asserts maybe_self_restart returns None on spawn failure
    EVEN when every other condition (stale, past cooldown, idle) says restart.
    """
    def _fake_respawn_fail(argv=None):
        return False

    monkeypatch.setattr(SR, "respawn_self", _fake_respawn_fail)
    # Force the decision core to say "restart" by stubbing its inputs.
    monkeypatch.setattr(SR, "gather", lambda agent: {
        "stamped_sha": "a" * 12, "head_sha": "b" * 12, "commits_behind": 7})
    monkeypatch.setattr(SR, "_min_behind", lambda: 1)
    monkeypatch.setattr(SR, "_min_uptime_s", lambda: 0.0)

    reason = SR.maybe_self_restart("t376agent", in_flight=False)
    assert reason is None, (
        "maybe_self_restart returned a reason despite the respawn FAILING — "
        "the caller would then exit 0 with no successor and stay down forever "
        "(N1: the daemon does not contest a deliberate exit). Failed respawn "
        "must mean KEEP RUNNING (return None).")


# ------------------------------------------------------------------ S1-P4
def test_s1_p4_successful_respawn_precedes_the_reason(monkeypatch):
    """Mirror image of P3: when respawn_self SUCCEEDS, maybe_self_restart must
    return the reason (the caller may then exit 0 — the successor exists). The
    ORDER is the contract: respawn was CALLED and returned True before any
    reason was returned.
    """
    order = []

    def _fake_respawn_ok(argv=None):
        order.append("respawn")
        return True

    monkeypatch.setattr(SR, "respawn_self", _fake_respawn_ok)
    monkeypatch.setattr(SR, "gather", lambda agent: {
        "stamped_sha": "a" * 12, "head_sha": "b" * 12, "commits_behind": 7})
    monkeypatch.setattr(SR, "_min_behind", lambda: 1)
    monkeypatch.setattr(SR, "_min_uptime_s", lambda: 0.0)
    # worklive write is a side effect we don't care about here; stub it.
    import core.comm.liveness as _liv
    monkeypatch.setattr(_liv, "worklive", lambda agent: type(
        "_FakeLive", (), {"set": lambda *a, **k: None})())

    reason = SR.maybe_self_restart("t376agent", in_flight=False)
    assert reason is not None, "successful respawn must yield a reason to stand down on"
    assert order == ["respawn"], \
        f"respawn must precede the reason return; got order {order!r}"
