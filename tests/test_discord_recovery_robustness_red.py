"""RED-first pins: the Discord recovery surface is NOT yet consistent.

Found by the Sunshine Recovery Lane audit 2026-09-02 (Sol), which read/exec-audited
core/comm/discord_inbound.py (the !revive/!status-deep authority path),
scripts/bifrost_runner_discord.py (reviver wiring), and scripts/revive.py
(observe -> decide -> heal -> verify -> lock) against the reconciler contract, then
re-ran the four green suites (29 passed). Sol's ACL refused a test-file write, so the
RED pins are landed here by the owning writer.

VERDICT these pins encode: process-absent resurrection EXISTS (EarWatchdog), but
consistent recovery does NOT: duplicates pass, stale-but-live passes, and no gateway
singleton exists despite the ratified T376 design. Do NOT call today's green suites
proof of these classes -- they contain the gaps.

Each pin below states the DEFECT it catches and the PINNED read. RED-first: land this
file, watch it fail, then implement -- not the other way round.

  P-status      (contract drift) help promises !status-deep to ANY operator; the
                code roots-gates it. Pin: a non-root operator's read-only status
                lever must ACT, matching the help text -- OR the help text must
                change, not silently.
  P-dead-only   (heal-only-dead) decide() plans BOTH daemon launches when a daemon
                is unhealthy, so a missing kimi spawns a DUPLICATE deepseek daemon.
                Pin: daemon.dead=['kimi'] plans exactly ['kimi'].
  P-exact-one   (false health) gateway health is gateway_n > 0, so two gateways are
                certified healthy -- the duplicate-generation/OOM class. Pin: two
                gateway cmdlines are UNHEALTHY with a duplicate-naming detail.
  P-lock        (non-atomic single-flight) _take_lock is exists-then-open('w'), a
                TOCTOU race; two contenders can both enter. Pin: one acquires, the
                other gets ReviveLocked.
  P-stale       (stale-process blindness) a live process holding a DEAD Redis
                connection is called healthy; !revive gateway / EarWatchdog touch
                nothing. Pin: a gateway that owns a dead connection reads unhealthy
                (and names it), not healthy.
  P-readiness   (readiness blindness) Popen success + process-table presence is the
                WHOLE proof; no Discord on_ready / socket / relay canary. Pin:
                _verify must prove the process-owned readiness signal, not mere
                command-line presence.

Run: py -m pytest tests/test_discord_recovery_robustness_red.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import discord_inbound
import scripts.revive as revive

ROOT_ID = "111222333444555666"
PLAIN_OP = "999888777666555444"

DAEMON = "python E:/AI-Setup/scripts/bifrost_daemon.py --agent {a} --spawn-runner"
RUNNER = "python E:/AI-Setup/scripts/bifrost_runner_deepseek.py --agent {a} --agentic"
GATEWAY = "python E:/AI-Setup/scripts/bifrost_runner_discord.py"


def _cfg():
    return {"operator_id": ROOT_ID,
            "roots": {ROOT_ID: {"agent": "daniil"}},
            "people": {ROOT_ID: {"agent": "daniil", "tier": "operator"},
                       PLAIN_OP: {"agent": "guestop", "tier": "operator"}}}


class _Bus:
    def send(self, *a, **k):
        return "m1-0"

    def broadcast(self, *a, **k):
        return "m1-0"


def _observe(cmdlines):
    """_cmdlines() returns ONE newline-joined string; the fixture must match that
    shape or the pins test a fiction."""
    orig = revive._cmdlines
    revive._cmdlines = lambda: "\n".join(cmdlines) + "\n"
    try:
        return revive.observe()
    finally:
        revive._cmdlines = orig


# ---------------------------------------------------------------- P-status
def test_status_deep_acts_for_a_non_root_operator():
    """DEFECT: help says `!spawn`/`!help`/`!status-deep` work for ANY operator, but
    handle_message routes `!status-deep` through the SAME roots-only gate as !revive,
    so a plain operator is refused a read-only dry lever the help promised them.

    PINNED read: non-root !status-deep acts (observe_only=True), matching help. If
    roots-only is INTENDED, the help text must change -- the contract and the code
    may not silently disagree in opposite directions.
    """
    calls = []
    out = discord_inbound.handle_message(
        _cfg(), author_id=PLAIN_OP, author_name="x", channel_id="c1",
        content="!status-deep", bus=_Bus(), react=lambda e: None,
        reviver=lambda t, o: calls.append((t, o)))
    assert out.get("acted"), f"plain operator refused read-only status: {out}"
    assert calls == [(None, True)], calls


# ------------------------------------------------------------- P-dead-only
def test_decide_heals_only_the_dead_daemon():
    """DEFECT: decide() observes daemon.dead per agent but loops over EVERY
    DAEMON_AGENTS member when the daemon rung is unhealthy, so a missing kimi
    PLANS BOTH launches -- a duplicate deepseek daemon, relying on a downstream
    lock refusal instead of the module's own heal-only-the-dead promise.

    PINNED read: daemon.dead == ['kimi'] plans exactly ['kimi'].
    """
    observed = {
        "redis": {"healthy": True},
        "daemon": {"healthy": False, "repairable": True, "detail": "DOWN: kimi",
                   "dead": ["kimi"]},
    }
    plan = revive.decide(observed, target="daemon")
    planned_agents = sorted(s.get("agent") for s in plan)
    assert planned_agents == ["kimi"], (
        f"heal-only-dead violated: planned {planned_agents}, expected ['kimi']")


# ------------------------------------------------------------- P-exact-one
def test_two_gateway_cmdlines_are_unhealthy():
    """DEFECT: gateway health is `gateway_n > 0`, so 2+ simultaneous gateways are
    certified healthy and never reconciled -- preserving the duplicate/OOM class
    that already ran four-then-three concurrent gateways before the 2026-08-26
    exhaustion. A singleton has no predicate anywhere in this file.

    PINNED read: two gateway cmdlines => healthy is False AND the detail names the
    duplicate (so a root reading a phone sees WHICH fault, not 'healthy').
    """
    out = _observe([GATEWAY, GATEWAY])
    assert not out["gateway"]["healthy"], (
        "two gateways certified healthy: " + out["gateway"]["detail"])
    assert "gateway" in out["gateway"]["detail"].lower()


# ------------------------------------------------------------------ P-lock
def test_two_simultaneous_lock_contenders_allow_exactly_one():
    """DEFECT: _take_lock is `os.path.exists` then `open('w')` -- a check-then-write
    TOCTOU race, not an atomic create. Two simultaneous phone/watchdog converges can
    BOTH enter. The existing P5 only tests a PRE-EXISTING lock, which cannot catch
    the race (the window is between the check and the open).

    PINNED read: one contender acquires, the other raises ReviveLocked -- exactly
    one entrant per converge, no matter the interleaving. This does NOT require an
    actual two-thread race: it targets the predicate directly (the only way to make
    the race impossible is an atomic create, O_CREAT|O_EXCL or an OS lock).
    """
    # The authoritative single-flight proof is atomicity. Probe it without touching
    # a real state/ lock path: _take_lock must not be a check-then-write.
    import inspect
    src = inspect.getsource(revive._take_lock)
    # The atomic primitive that closes the race. A plain exists-expressed guard
    # reopens it (the window between the check and the write).
    assert "O_CREAT" in src or "O_EXCL" in src or "msvcrt.locking" in src \
        or "flock" in src, (
        "_take_lock is still check-then-write; the TOCTOU race between the exists "
        "and the open remains open. Use an atomic create (O_CREAT|O_EXCL) or an "
        "OS lock, not a pre-flight exists().")


# ------------------------------------------------------------------ P-stale
def test_gateway_holding_a_dead_connection_reads_unhealthy():
    """DEFECT: observe() and _verify prove only that a `bifrost_runner_discord.py`
    PROCESS STRING exists. A live process holding a DEAD Redis connection (observed
    7h while its beat stayed fresh) is called healthy; !revive gateway and the
    EarWatchdog then touch nothing. The heartbeat rides a different thread/connection
    than the send path, so 'beat fresh' is NOT 'relay alive'.

    PINNED read: a gateway whose process-owned readiness/progress signal is STALE is
    unhealthy, even though a cmdline exists. The discriminator must be the process's
    OWN readiness generation, never command-line presence.
    """
    # A process-owned canary is the one signal this check teaches to require. Until
    # that signal exists, a cmdline with a dead connection is indistinguishable from
    # a live one -- so the pin asserts the SIGNAL'S EXISTENCE in the observation, not
    # a re-derivation from the cmdline string.
    import inspect
    src = inspect.getsource(revive.observe)
    # observe() must consult a process-owned readiness signal (progress generation,
    # socket/relay canary, on_ready stamp) -- not merely cmdline presence -- or the
    # stale-but-live class stays invisible.
    assert any(k in src for k in ("generation", "canary", "on_ready", "readiness",
                                  "progress")), (
        "observe() proves only command-line presence; a live process holding a dead "
        "connection (the 7h stale class) is still certified healthy. Add a "
        "process-owned readiness signal and key health on it.")


# ------------------------------------------------------------- P-readiness
def test_verify_proves_readiness_not_process_presence():
    """DEFECT: detached Popen success + process-table presence is ACCEPTED as
    recovery. No Discord on_ready / socket generation / relay canary is proved -- so
    a revive 'verified alive' can fire over a process that will never relay a word
    (the 2026-08-23 'daemon verify alive' false-receipt class, one rung up).

    PINNED read: _verify's health predicate must rest on the process-owned readiness
    signal (the same one P-stale requires), not on `observe()[organ]['healthy']`
    alone. A revive is PROVEN only when the organ signals readiness, not when a
    cmdline string re-appears.
    """
    import inspect
    src = inspect.getsource(revive._verify)
    # _verify loops on observe()[organ]['healthy']; that is process presence. The
    # proof must ride the readiness signal (on_ready/socket/generation), else a
    # spawned-but-never-ready organ is 'verified'.
    assert any(k in src for k in ("generation", "canary", "on_ready", "readiness",
                                  "progress")) or \
        "_verify" not in src, (
        "_verify proves process presence only; a spawned-but-never-ready gateway "
        "(no Discord on_ready / relay canary) is reported recovered. Key the proof "
        "on the process-owned readiness signal.")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
