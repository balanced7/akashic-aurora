"""W156b pins: the Redis endpoint follows the WORLD, not a tracked constant.

W156 built `core/world.py` -- resolution, guards, provenance. This file pins the part
that actually moves traffic: the foundation's default endpoint must be a function of
which world the process is standing in.

THE MEASURED DEFECT (2026-08-14, alpha clone, before this wiring):
    core.world.current()          -> alpha, redis 16381
    config.REDIS_PORT             -> 16379
    redis_connection.DEFAULT_...  -> 16379   <-- traffic still lands in PROD

    A resolver nothing consults is a resolver that does not exist. Building `world.py`
    and stopping there would have reproduced the exact defect it was written to close:
    a field that describes a world without deciding one.

PRECEDENCE, and why it is this order:
    1. REDIS_HOST / REDIS_PORT env  -- unchanged, still highest. The whole test suite
       and every ad-hoc probe depends on it; a slice that quietly demoted it would
       break isolation for tests in order to add isolation for worlds.
    2. the world                    -- NEW. The per-checkout answer.
    3. config.REDIS_PORT            -- unchanged fallback, for UNKNOWN checkouts and
       for any environment where core.world cannot import.

WHAT THIS SLICE DELIBERATELY DOES NOT DO. It does not plumb `assert_may_write()` into
the write paths. An UNKNOWN checkout still falls back to config (prod) for READS, loudly.
Wiring a refusal into half the write doors is worse than not wiring it: it buys the
feeling of a guard while leaving the holes that matter, which is the failure the house
already named in `gate_at_module_level_hides_dead_capability_inside_it`. The write-side
guard is its own fenced slice, and it is named in the handoff rather than half-built here.
"""
import importlib
import os

import pytest


def _fresh(monkeypatch, **env):
    """Re-import the foundation with a chosen environment -- its endpoint is resolved
    at MODULE IMPORT into DEFAULT_REDIS_PORT, so a test that only sets env after import
    would be testing nothing."""
    for k in ("REDIS_HOST", "REDIS_PORT", "REDIS_DB", "AKASHIC_WORLD"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import core.foundation.redis_connection as rc
    return importlib.reload(rc)


def test_w1_alpha_checkout_dials_alpha(monkeypatch):
    """The headline. This checkout IS alpha; its traffic must not reach 16379."""
    rc = _fresh(monkeypatch, AKASHIC_WORLD="alpha")
    assert rc.DEFAULT_REDIS_PORT == 16381


def test_w2_beta_checkout_dials_beta(monkeypatch):
    rc = _fresh(monkeypatch, AKASHIC_WORLD="beta")
    assert rc.DEFAULT_REDIS_PORT == 16380


def test_w3_prod_is_unchanged(monkeypatch):
    """The no-regression pin. In prod the world resolves to prod and the answer is
    byte-identical to what config always said -- this slice must be invisible there."""
    rc = _fresh(monkeypatch, AKASHIC_WORLD="prod")
    import config
    assert rc.DEFAULT_REDIS_PORT == config.REDIS_PORT == 16379


def test_w4_env_still_wins_over_the_world(monkeypatch):
    """Tests, probes and one-off tools set REDIS_PORT directly. Demoting env below
    the world would break isolation for tests in order to add it for worlds."""
    rc = _fresh(monkeypatch, AKASHIC_WORLD="alpha", REDIS_PORT="16399")
    assert rc.DEFAULT_REDIS_PORT == 16399


def test_w5_unknown_world_falls_back_to_config_but_says_so(monkeypatch, capsys):
    """An UNKNOWN checkout still reads (per W156 S2b) -- but silence here would be the
    original defect wearing a new coat, so the fallback must announce itself."""
    monkeypatch.setenv("AKASHIC_WORLD", "nonsense-world")
    import core.foundation.redis_connection as rc
    importlib.reload(rc)
    import config
    assert rc.DEFAULT_REDIS_PORT == config.REDIS_PORT
    warned = capsys.readouterr()
    assert "world" in (warned.out + warned.err).lower()


def test_w7_a_foreign_worlds_port_in_the_env_is_declined_not_obeyed(monkeypatch, capsys):
    """The typo case, and the only path that can aim a twin at another world: a stale
    REDIS_PORT exported in one shell. The override is dropped, the world's own endpoint
    stands, and both are said out loud."""
    rc = _fresh(monkeypatch, AKASHIC_WORLD="alpha", REDIS_PORT="16379")
    assert rc.DEFAULT_REDIS_PORT == 16381, "a twin obeyed prod's port from the environment"
    said = capsys.readouterr().out + capsys.readouterr().err
    assert "16379" in said or "IGNORING" in said


def test_w8_declining_never_raises_at_import(monkeypatch):
    """core/paths.py's rule for this exact position: a helper that throws during import
    takes down every door that imports it. A stale env var must not brick the twin."""
    rc = _fresh(monkeypatch, AKASHIC_WORLD="alpha", REDIS_PORT="16380")
    assert rc.DEFAULT_REDIS_PORT == 16381        # got here at all == it did not raise


def test_w9_an_unregistered_port_is_still_obeyed(monkeypatch):
    """The suite and every ad-hoc probe steer with throwaway ports. A guard that fought
    them would be disabled within a week, so it fires only on REGISTERED foreign worlds."""
    rc = _fresh(monkeypatch, AKASHIC_WORLD="alpha", REDIS_PORT="16399")
    assert rc.DEFAULT_REDIS_PORT == 16399


def test_w6_the_endpoint_agrees_with_the_world_object(monkeypatch):
    """Two resolvers that can disagree WILL disagree. Pin them to one answer."""
    for name, port in (("alpha", 16381), ("beta", 16380), ("prod", 16379)):
        rc = _fresh(monkeypatch, AKASHIC_WORLD=name)
        from core import world as W
        assert W.resolve(env={"AKASHIC_WORLD": name}).redis_port == rc.DEFAULT_REDIS_PORT == port
