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
(no cursor advance and one causal reply) survives in
BOTH postures; only the file-mutation prohibition is lifted when writable.

SUNSHINE'S BLOCKER (2026-09-02, bus review of faf124c2->10eabcda) -- the second
half of this file. The static gate above proves only the POLICY shape. The wire
defeats it: core/comm/discord_inbound.py relays a Discord GUEST into a seat lane
through `Bus("daniil")` ("inbound speaks AS the operator, or not at all"), so the
message arrives frm='daniil' + meta.source='discord' -- satisfying the installed
privileged policy exactly -- while carrying operator=False, guest=True,
authority='none'. A guest in Sunshine's channel could spend a writable/GUI turn.
Serge is the non-theoretical second case: a real operator-tier id that is not root.

THE LAW THIS ADDS: `frm` is GATEWAY ATTRIBUTION, never proof of speaker. A
privileged turn must prove operator provenance PER MESSAGE, and must FAIL CLOSED
when the proof is absent (an unstamped message is refused, never assumed root).
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
        agent_id="sol",
        callsign="Sunshine",
        status="historical-unratified",
        authority="registry",
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
    # ...but every standing safety clause SURVIVES
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


# ===================================================================== the blocker
# Exact wire shapes, copied from core/comm/discord_inbound.py. `frm` is "daniil"
# for BOTH because the gateway is Bus("daniil") -- that is the whole point.
from core.comm import packet_spec  # noqa: E402
from core.comm.bus import Bus  # noqa: E402


class _NoClient:
    pass


def _wire(meta: dict, *, frm: str = "daniil", kind: str = "chat"):
    fields = {
        "frm": frm,
        "to": "sol",
        "kind": kind,
        "content": json.dumps("do the thing"),
        "parts": "[]",
        "meta": json.dumps(meta),
        "ts": "2026-09-02T21:00:00+00:00",
    }
    packet_spec.stamp(fields)
    return Bus("sol", client=_NoClient(), promote=False)._to_msg("90-0", fields)


def _guest_message():
    """discord_inbound.py:533 -- the guest relay, verbatim shape."""
    return _wire({
        "source": "discord", "operator": False, "guest": True,
        "authority": "none", "guest_name": "somebody", "guest_id": "999",
        "lane": "seat-channel",
    })


def _root_operator_message():
    """The operator relay once the gateway stamps authenticated provenance."""
    return _wire({
        "source": "discord", "operator": True, "speaker": "daniil",
        "operator_id": "111", "root": True, "lane": "seat-channel",
    })


def _non_root_operator_message():
    """Serge: a real operator-tier id that is NOT root (R1 v2)."""
    return _wire({
        "source": "discord", "operator": True, "speaker": "simon",
        "operator_id": "222", "root": False, "lane": "seat-channel",
    })


def test_the_static_policy_alone_cannot_tell_a_guest_from_the_operator():
    """The bypass itself, pinned: policy.accepts() says YES to the guest wire."""
    policy = _operator_policy()
    assert policy.accepts(_guest_message()) is True   # <-- why the gate was not enough
    assert policy.accepts(_root_operator_message()) is True


def test_privileged_turn_refuses_the_exact_guest_wire_shape():
    prof = WakeProfile(allow_write=True)
    assert WakeProfile.admits_message(prof, _guest_message()) is not None


def test_privileged_turn_admits_the_authenticated_root_operator():
    for prof in (WakeProfile(allow_write=True), WakeProfile(allow_gui=True)):
        assert WakeProfile.admits_message(prof, _root_operator_message()) is None


def test_privileged_turn_refuses_an_operator_who_is_not_root():
    prof = WakeProfile(allow_gui=True)
    assert WakeProfile.admits_message(prof, _non_root_operator_message()) is not None


def test_privileged_admission_fails_closed_on_an_unstamped_message():
    """Absence of proof is refusal -- never 'assume root because frm says daniil'."""
    prof = WakeProfile(allow_write=True)
    legacy = _wire({"source": "discord", "operator": True, "speaker": "daniil"})
    assert WakeProfile.admits_message(prof, legacy) is not None


def test_read_only_turns_are_unaffected_by_the_provenance_gate():
    """The ordinary read-only wake must keep answering guests and everyone else."""
    prof = WakeProfile()
    assert WakeProfile.admits_message(prof, _guest_message()) is None
    assert WakeProfile.admits_message(prof, _non_root_operator_message()) is None


# --------------------------------------------- secondary findings (Sunshine's list)
def test_gui_only_instructions_do_not_contradict_themselves():
    """Was: posture said 'read-only' then announced GUI actuation. Split the axes."""
    text = wake_developer_instructions("sol", _identity(), WakeProfile(allow_gui=True))
    low = text.lower()
    assert "filesystem read-only" in low
    assert "gui" in low
    # the bare contradiction must be gone
    assert "narrowly scoped, read-only" not in low


def test_the_per_turn_prompt_also_follows_the_posture():
    """THE FIFTH HARDCODE. Sunshine's list named four knobs; build_wake_prompt was a
    fifth, and a writable turn told 'make no mutations in this turn' is handed a flat
    contradiction -- the GUI-posture bug in a second location."""
    from agent.harness.codex_bifrost_wake import build_wake_prompt

    msg = _root_operator_message()
    ro = build_wake_prompt("sol", msg, identity=_identity(), profile=WakeProfile())
    assert "Work read-only" in ro
    assert "make no file" in ro

    rw = build_wake_prompt(
        "sol", msg, identity=_identity(), profile=WakeProfile(allow_write=True)
    )
    assert "Work read-only" not in rw
    assert "make no file" not in rw
    assert "workspace-write" in rw
    # the rest of the safety boundary is untouched by posture
    for clause in ("cursor", "second bus reply"):
        assert clause in rw and clause in ro


def test_prompt_default_posture_is_read_only():
    """An un-passed profile must never silently grant write."""
    from agent.harness.codex_bifrost_wake import build_wake_prompt

    text = build_wake_prompt("sol", _root_operator_message(), identity=_identity())
    assert "Work read-only" in text


def test_gateway_stamps_authenticated_provenance_on_operator_messages():
    """The gateway half: an operator relay must carry WHO, not just 'operator: true'."""
    import inspect
    from core.comm import discord_inbound

    src = inspect.getsource(discord_inbound.handle_message)
    assert '"operator_id"' in src and '"root"' in src
