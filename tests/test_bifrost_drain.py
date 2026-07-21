"""bifrost-drain pins — the graceful runner exit (the restart-tax killer).

Born 2026-07-21 night: activating the storm wiring took TaskStop (tree-kill ghost --
the W08 class: wrapper died, python child survived, lock lingered), a sleep-retry
dance, and threw away the runner's in-flight context. The drain flag is the fix:
finish the current message, release the lock, exit 0 at the next loop top.

  P1  drain/drain_requested/clear_drain round-trip (namespaced control plane)
  P2  the flag carries a TTL -- an unhonored request self-clears (C1-9 law at birth)
  P3  the CLI verb parses and sets the flag through control
  P4  offline bus -> drain refuses loudly (rc 1), never half-requests
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from core.comm import control


class Ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, k):
        return None


def _ns_env(monkeypatch):
    ns = f"t-drain-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", ns)
    return ns


def _online():
    from core.comm.bus import Bus
    return Bus("t-drain").online


def test_p1_drain_roundtrip(monkeypatch):
    _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    agent = f"t-drain-{uuid.uuid4().hex[:6]}"
    assert control.drain_requested(agent) is None
    assert control.drain(agent, by="tester", reason="wiring change")
    rec = control.drain_requested(agent)
    assert rec and rec["by"] == "tester" and "wiring" in rec["reason"]
    control.clear_drain(agent)
    assert control.drain_requested(agent) is None


def test_p2_flag_carries_ttl(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    agent = f"t-drain-ttl-{uuid.uuid4().hex[:6]}"
    control.drain(agent, by="tester")
    ttl = Bus("t-drain")._client.ttl(f"{ns}:control:drain:{agent}")
    assert 0 < ttl <= control.DRAIN_TTL_S, \
        "an unhonored drain must self-clear -- never a forever-flag"


def test_p3_cli_verb_sets_flag(monkeypatch):
    p = agent_cli.build_parser()
    a = p.parse_args(["bifrost-drain", "claude", "--to", "deepseek", "--reason", "reload"])
    assert a.fn is agent_cli.cmd_bifrost_drain and a.to == "deepseek"
    seen = {}

    def fake_drain(agent, by="user", reason=""):
        seen.update(agent=agent, by=by, reason=reason)
        return True

    monkeypatch.setattr(control, "drain", fake_drain)
    rc = agent_cli.cmd_bifrost_drain(Ns(agent_id="claude", to="deepseek", reason="reload"))
    assert rc == 0 and seen == {"agent": "deepseek", "by": "claude", "reason": "reload"}


def test_p4_offline_refuses_loudly(monkeypatch):
    monkeypatch.setattr(control, "drain", lambda *a, **k: False)
    rc = agent_cli.cmd_bifrost_drain(Ns(agent_id="claude", to="deepseek", reason=""))
    assert rc == 1
