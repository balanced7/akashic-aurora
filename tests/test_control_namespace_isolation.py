"""
Fix A regression pins (RB-25 drill 3 finding, 2026-07-12): the control plane
(pause / halt / narration) must be NAMESPACE-SCOPED, so a runner in an isolated
BIFROST_NAMESPACE can never freeze the live 'bifrost' fleet.

Before the fix, control.PAUSE_KEY was hardcoded to 'bifrost', so a drill runner that
tripped the reply rate-limit guard paused the REAL bus. These pins prove the control
keys now follow BIFROST_NAMESPACE like Bus.ns does.

Uses throwaway namespaces ('test_ctrl_a'/'test_ctrl_b') only -- it never reads or writes
the real 'bifrost' control keys, so running it cannot disturb a live fleet.
"""
import os

import pytest

from core.comm import control

NS_A = "test_ctrl_a"
NS_B = "test_ctrl_b"


def _bus_online() -> bool:
    return control._client() is not None


pytestmark = pytest.mark.skipif(not _bus_online(), reason="bus/Redis offline")


@pytest.fixture(autouse=True)
def _clean_env_and_keys(monkeypatch):
    """Scrub both throwaway namespaces before and after each test; leave the real bus alone."""
    def _wipe():
        for ns in (NS_A, NS_B):
            monkeypatch.setenv("BIFROST_NAMESPACE", ns)
            control.resume()          # clears the global pause AND every per-agent halt in this ns
    _wipe()
    yield
    _wipe()
    monkeypatch.delenv("BIFROST_NAMESPACE", raising=False)


def test_key_names_follow_namespace(monkeypatch):
    """_pause_key/_halt_prefix/_narration_key derive from BIFROST_NAMESPACE (default 'bifrost')."""
    monkeypatch.delenv("BIFROST_NAMESPACE", raising=False)
    assert control._pause_key() == "bifrost:control:paused"     # default preserved (no regression)
    assert control._halt_prefix() == "bifrost:control:halt:"
    monkeypatch.setenv("BIFROST_NAMESPACE", NS_A)
    assert control._pause_key() == f"{NS_A}:control:paused"
    assert control._narration_key() == f"{NS_A}:control:narration"


def test_pause_is_namespace_isolated(monkeypatch):
    """The core pin: pausing namespace A must NOT pause namespace B."""
    monkeypatch.setenv("BIFROST_NAMESPACE", NS_A)
    assert control.pause(reason="isolation-pin", by="test") is True
    assert control.is_paused() is True

    monkeypatch.setenv("BIFROST_NAMESPACE", NS_B)
    assert control.is_paused() is False, "namespace B saw namespace A's pause -- NOT isolated"

    # resuming B must leave A's pause standing
    control.resume()
    monkeypatch.setenv("BIFROST_NAMESPACE", NS_A)
    assert control.is_paused() is True, "resuming B cleared A's pause -- NOT isolated"


def test_is_halted_is_namespace_isolated(monkeypatch):
    """is_halted (the gate every runner checks) must respect the namespace for both pause and halt."""
    agent = "runner-x"
    # global pause in A halts A's agents, not B's
    monkeypatch.setenv("BIFROST_NAMESPACE", NS_A)
    control.pause(reason="halt-pin", by="test")
    assert control.is_halted(agent) is True
    monkeypatch.setenv("BIFROST_NAMESPACE", NS_B)
    assert control.is_halted(agent) is False, "pause in A halted an agent in B -- NOT isolated"

    # per-agent targeted halt in B stays in B
    control.halt(targets=[agent], reason="targeted", by="test")
    assert control.is_halted(agent) is True
    monkeypatch.setenv("BIFROST_NAMESPACE", NS_A)
    # A still only has its global pause; B's targeted halt is invisible here
    assert control.is_halted("some-other-agent") is True   # A's global pause still applies to A
    control.resume()
    assert control.is_halted("some-other-agent") is False   # A cleared; B's targeted halt untouched
    monkeypatch.setenv("BIFROST_NAMESPACE", NS_B)
    assert control.is_halted(agent) is True, "clearing A wiped B's targeted halt -- NOT isolated"
