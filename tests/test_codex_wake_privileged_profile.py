"""RED contracts (committed before implementation, M3) for the operator-gated
writable/GUI wake profile -- step 0 of the screenspace organ (T386).

WHY THIS EXISTS
---------------
Sunshine's wake adapter is hardcoded read-only at four knobs (thread sandbox,
turn sandboxPolicy, ToolBox allow_write, developer instructions). Her own spec
(bus 1788380940130-0) asks for an explicit `--allow-write`/`--allow-gui` profile
that keeps read-only as the default and that ONLY an authenticated operator
Discord message may request. This file pins that contract.

THE LOAD-BEARING INVARIANT
--------------------------
Read-only is the floor. Any privilege above it (write or GUI) is refused UNLESS
the wake's admission policy is operator-gated: every admitted sender is an
operator, the source is the operator channel, and the sender set is non-empty.
A privileged profile paired with a policy that would admit anyone else, or a
non-operator source, MUST refuse at construction -- never arm a writable seat
that a non-operator can trigger. Everything Sunshine listed as preserved
(Rill non-interference, no cursor advance, single causal reply) survives in
BOTH postures; only the file-mutation prohibition is lifted when writable.
"""
from __future__ import annotations

import json

import pytest

from agent.harness.codex_bifrost_wake import (
    OPERATOR_SENDERS,
    OPERATOR_SOURCE,
    WakePolicy,
    WakeError,
    WakeProfile,
    wake_developer_instructions,
)
from agent.harness.codex_bifrost_wake import SubjectIdentity
from scripts.codex_bifrost_wake import build_parser


def _operator_policy(**over) -> WakePolicy:
    base = dict(
        agent="sol",
        allowed_senders=frozenset({"daniil"}),
        direct_kinds=frozenset({"chat"}),
        required_source="discord",
    )
    base.update(over)
    return WakePolicy(**base)


def _identity() -> SubjectIdentity:
    return SubjectIdentity(
        callsign="Sunshine", status="historical-unratified", authority="registry"
    )


# --------------------------------------------------------------- profile shape
def test_default_profile_is_read_only_floor():
    p = WakeProfile()
    assert p.allow_write is False and p.allow_gui is False
    assert p.privileged is False
    assert p.thread_sandbox == "read-only"
    assert p.turn_sandbox_policy() == {"type": "readOnly", "networkAccess": False}


def test_write_profile_maps_all_sandbox_knobs_together():
    p = WakeProfile(allow_write=True)
    assert p.privileged is True
    assert p.thread_sandbox == "workspace-write"
    assert p.turn_sandbox_policy() == {"type": "workspaceWrite", "networkAccess": False}


def test_gui_is_a_separate_capability_from_write():
    """GUI actuation needs no filesystem write; it is privileged on its own."""
    p = WakeProfile(allow_gui=True)
    assert p.privileged is True          # gui alone still trips the operator gate
    assert p.allow_write is False
    assert p.thread_sandbox == "read-only"  # sandbox keys off write, not gui


# ------------------------------------------------------ the operator-gate invariant
def test_privileged_profile_requires_operator_gated_policy():
    prof = WakeProfile(allow_write=True)
    # OK: operator-only, discord-sourced
    WakeProfile.require_operator_gate(prof, _operator_policy())


def test_privileged_refuses_a_non_operator_sender():
    prof = WakeProfile(allow_write=True)
    bad = _operator_policy(allowed_senders=frozenset({"daniil", "deepseek"}))
    with pytest.raises(WakeError):
        WakeProfile.require_operator_gate(prof, bad)


def test_privileged_refuses_a_non_operator_source():
    prof = WakeProfile(allow_gui=True)
    bad = _operator_policy(required_source="bus")
    with pytest.raises(WakeError):
        WakeProfile.require_operator_gate(prof, bad)


def test_privileged_refuses_an_empty_sender_set():
    """frozenset() is a subset of every set -- the gate must not read it as safe."""
    prof = WakeProfile(allow_write=True)
    bad = _operator_policy(allowed_senders=frozenset())
    with pytest.raises(WakeError):
        WakeProfile.require_operator_gate(prof, bad)


def test_read_only_profile_needs_no_gate():
    prof = WakeProfile()
    # a read-only wake with the ordinary dsh_agent policy must NOT be gated
    WakeProfile.require_operator_gate(prof, _operator_policy(
        allowed_senders=frozenset({"dsh_agent"}), required_source=None,
    ))


def test_operator_constants_are_what_the_installer_uses():
    assert "daniil" in OPERATOR_SENDERS
    assert OPERATOR_SOURCE == "discord"


# ------------------------------------------------ developer instructions per posture
def test_read_only_instructions_forbid_mutation():
    text = wake_developer_instructions("sol", _identity(), WakeProfile())
    low = text.lower()
    assert "read-only" in low
    assert "do not edit files" in low or "make no file" in low or "no file" in low


def test_writable_instructions_lift_only_the_mutation_clause():
    text = wake_developer_instructions("sol", _identity(), WakeProfile(allow_write=True))
    low = text.lower()
    # the blanket read-only prohibition is gone...
    assert "do not edit files or durable state" not in low
    # ...but every other safety clause SURVIVES
    assert "rill" in low                      # non-interference preserved
    assert "cursor" in low                     # never advance a bus cursor
    assert "one final" in low or "single" in low or "one peer-facing" in low  # single reply


def test_gui_instructions_announce_screenspace_capability():
    text = wake_developer_instructions("sol", _identity(), WakeProfile(allow_gui=True))
    assert "gui" in text.lower() or "screen" in text.lower()


# --------------------------------------------------------------------- CLI surface
def test_cli_exposes_allow_write_and_allow_gui_defaulting_off():
    args = build_parser().parse_args(["--agent", "sol"])
    assert args.allow_write is False
    assert args.allow_gui is False


def test_cli_allow_write_and_gui_parse_independently():
    a = build_parser().parse_args(["--allow-write"])
    assert a.allow_write is True and a.allow_gui is False
    b = build_parser().parse_args(["--allow-gui"])
    assert b.allow_gui is True and b.allow_write is False
