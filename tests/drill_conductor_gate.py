"""RED-pin drill for core/comm/conductor_gate.py -- every pin must PASS before the gate
can activate anything. Pure decision-core pins use injected probes, no live outage needed.

Run: py -m pytest tests/drill_conductor_gate.py -q
"""
import inspect

import pytest

from core.comm.conductor_gate import (
    MANDATE_MAX_HOURS, MANDATE_MAX_ROLE, MANDATE_MAX_SCOPE,
    decide_and_act, evaluate_succession, grant_mandate_caps, require_cap,
    acting_conduct_grant,
)
from core.trust.capabilities import Cap

# Fixture probes: each forces ONE condition so the rest are held constant.
def reap_alive(agent):
    return "alive"                    # K7: idle-but-alive -> not provably dead

def reap_orphan(agent):
    return "orphan (marker 99m stale, chain broken at pid 1234 (dead))"

def att_attended(agent):
    return "ATTENDED"

def att_unattended(agent):
    return "UNATTENDED"

def att_mix(agent):
    return "UNATTENDED" if agent == "claude" else "ATTENDED"

def op_absent():
    return False

def op_present():
    return True


def test_P1_idle_but_alive_conductor_does_not_activate():
    v = evaluate_succession(reap_fn=reap_alive, att_fn=att_attended, op_present_fn=op_absent)
    assert not v.activate, v.reason

def test_P1b_watcher_alive_beats_attendance_unattended_two_factor():
    v = evaluate_succession(reap_fn=reap_alive, att_fn=att_unattended, op_present_fn=op_absent)
    assert not v.activate, v.reason

def test_P2_fleet_wide_outage_does_not_activate():
    v = evaluate_succession(reap_fn=reap_orphan, att_fn=att_unattended, op_present_fn=op_absent)
    assert not v.activate, v.reason

def test_P3_active_operator_does_not_activate():
    v = evaluate_succession(reap_fn=reap_orphan, att_fn=att_mix, op_present_fn=op_present)
    assert not v.activate, v.reason

def test_P0_activation_fires_only_when_all_three_hold():
    v = evaluate_succession(agent_self="kimi", reap_fn=reap_orphan,
                            att_fn=att_mix, op_present_fn=op_absent)
    assert v.activate, v.reason
    assert v.successor == "deepseek", v.successor

def test_P4_permanent_grant_unexpressible_no_permanent_param():
    sig = inspect.signature(acting_conduct_grant)
    assert "permanent" not in sig.parameters, sig
    assert "hours" in sig.parameters
    assert sig.parameters["hours"].default is inspect.Parameter.empty  # required

def test_P5_self_widening_refused():
    with pytest.raises(PermissionError, match="self"):
        acting_conduct_grant(successor="deepseek", agent_id="deepseek",
                             role=MANDATE_MAX_ROLE, reason="pin", hours=1.0)

def test_P6_admin_grant_refused_by_allowlist():
    class FakeGrant:
        caps = set()
        path_scope = ["*"]
    with pytest.raises(PermissionError, match="admin.grant"):
        grant_mandate_caps(FakeGrant(), requested_caps=["admin.grant"], requested_scope=["core/"])

def test_P6_admin_approve_refused_by_allowlist():
    class FakeGrant:
        caps = set()
        path_scope = ["*"]
    with pytest.raises(PermissionError, match="admin.approve"):
        grant_mandate_caps(FakeGrant(), requested_caps=["admin.approve"], requested_scope=["core/"])

def test_P7_overbox_grant_refused_lapse_bounded():
    with pytest.raises(PermissionError):
        acting_conduct_grant(successor="deepseek", agent_id="navi",
                             role=MANDATE_MAX_ROLE, reason="pin",
                             hours=MANDATE_MAX_HOURS + 10.0)

def test_P7b_role_above_member_refused():
    with pytest.raises(PermissionError, match="member"):
        acting_conduct_grant(successor="deepseek", agent_id="navi",
                             role="admin", reason="pin", hours=1.0)

def test_require_cap_refuses_unknown_id():
    with pytest.raises(PermissionError):
        require_cap("some_unregistered_id", Cap.ADMIN_GRANT, action="pin probe")

def test_decide_and_act_dry_run_returns_without_emitting():
    v = decide_and_act(agent_self="kimi", reap_fn=reap_orphan, att_fn=att_mix,
                       op_present_fn=op_absent, dry_run=True)
    assert v.activate and v.successor == "deepseek", v.reason


# The REAL operator-presence read path (streams, not lists) -- exercised against a fake
# bus client so the pin deps on no live Redis.
def test_operator_present_reads_streams_correctly():
    import time as _t
    from core.comm.conductor_gate import _operator_recently_present

    class FakeClient:
        def __init__(self, rows):
            self._rows = rows
        def xrevrange(self, stream, count=None):
            return self._rows.get(stream, [])

    class FakeBus:
        online = True
        _bc_key = "ns:broadcast"
        def _inbox_key(self, agent):
            return f"ns:inbox:{agent}"
        def __init__(self, client):
            self._client = client

    now = _t.time()
    fields_bc = {"frm": "daniil", "ts": str(now - 10.0)}      # operator, fresh -> present
    rows = {"ns:broadcast": [("1-1", fields_bc)],
            "ns:inbox:conductor_gate": []}
    assert _operator_recently_present(bus=FakeBus(FakeClient(rows))) is True

    # stale operator message (older than window) -> not present
    fields_old = {"frm": "daniil", "ts": str(now - 99999.0)}
    rows_old = {"ns:broadcast": [("1-1", fields_old)],
                "ns:inbox:conductor_gate": []}
    assert _operator_recently_present(bus=FakeBus(FakeClient(rows_old))) is False

    # non-operator sender -> not present
    fields_peer = {"frm": "kimi", "ts": str(now - 10.0)}
    rows_peer = {"ns:broadcast": [("1-1", fields_peer)],
                 "ns:inbox:conductor_gate": []}
    assert _operator_recently_present(bus=FakeBus(FakeClient(rows_peer))) is False

    # offline / read error -> not present (fail closed)
    class OfflineBus:
        online = False
    assert _operator_recently_present(bus=OfflineBus()) is False

    class BrokenBus:
        online = True
        _bc_key = "ns:broadcast"
        def _inbox_key(self, agent):
            return f"ns:inbox:{agent}"
        def __init__(self):
            self._client = None          # xrevrange(...) will raise -> fail closed
    assert _operator_recently_present(bus=BrokenBus()) is False
