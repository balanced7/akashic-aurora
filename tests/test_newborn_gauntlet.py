"""
NEWBORN GAUNTLET -- trust half, hermetic (T029, battery sec. 2).

The live drill (2026-07-10) surfaced that a privileged agent ROLEPLAYING the newborn through
its own runner cannot test quarantine at all: every ToolBox door binds agent_id at runner
CONSTRUCTION (scripts/deepseek_chat.py:447 bifrost_inbox -> Bus(self.agent_id);
make_agentic_replier :199 agent_id=agent_id), so the doors the "newborn" touches are the
HOST's (admin) doors, never a stranger's. The trust boundary is enforced at the ACL layer --
so that is where it must be tested. This battery presents the genuinely-unknown id
`newborn-gauntlet-1` (absent from security/acl.json, absent from BOOTSTRAP_ROLES) at every
door the rubric's N3/N4 probe, and asserts deny-by-default. It is stronger than the roleplay
(adversarial USE beats review) and permanent.

Deepest finding pinned here: quarantine is airtight to the point that a newborn CANNOT SEND
ANY BUS KIND (bus_send_kinds = empty set). So "nothing -> one contribution" via a bus message
is impossible without a prior escalation grant -- the escalation door, not a self-made post,
is a newborn's only forward path. N6 (rubric) is corrected accordingly.

Run: py -m pytest tests/test_newborn_gauntlet.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trust.registry import resolve
from core.trust.capabilities import Cap
from core.comm import context_hints
from core.comm.promoter import ack_verdict

NEWBORN = "newborn-gauntlet-1"   # the pre-registered stranger: unknown to acl.json + bootstrap


# ---- N3/N4: the unknown id resolves quarantined, every door says no ----------

def test_unknown_id_resolves_quarantined():
    g = resolve(NEWBORN)
    assert g.role == "quarantined", "an id absent from acl.json + BOOTSTRAP_ROLES is quarantined"


def test_quarantined_holds_only_read_and_inbox():
    caps = resolve(NEWBORN).caps
    assert caps == {Cap.READ, Cap.BIFROST_INBOX}, \
        "deny-by-default: a stranger reads (boot/lookback/AGENTS.md) + its own inbox, nothing more"


def test_newborn_cannot_write_anywhere():
    g = resolve(NEWBORN)
    for path in ("core/comm/bus.py", "docs/anything.md", "security/acl.json", "README.md"):
        assert not g.can_write(path), f"quarantined write to {path} must be refused"


def test_newborn_has_no_exec():
    assert not resolve(NEWBORN).has(Cap.EXEC), \
        "no exec -> cannot run CLI verbs itself (the roleplay's own stated limit)"


def test_newborn_cannot_send_any_bus_kind():
    """THE deepest finding: bus_send_kinds is the EMPTY set, and BUS_SEND cap is absent -- a
    quarantined newborn cannot chat, request, handoff, hint, or ledger_update. It cannot even
    announce itself. Its only forward path is an escalation grant from a super_admin/human."""
    g = resolve(NEWBORN)
    for kind in ("chat", "request", "handoff", "reply", "note", "hint", "ledger_update",
                 "nudge", "steer", "inform", "decision", "blocker"):
        assert not g.can_send_kind(kind), f"quarantined must not send kind={kind}"
    assert g.bus_send_kinds == set(), "the allowlist is explicitly empty, not None(=all)"


# ---- N4a/N4b: the two control-plane forgeries the battery cares about most ----

def test_newborn_hint_is_dropped_at_the_fold_door():
    """N4d / RB-1: an authoritative-context hint from the stranger is refused at the fold door
    (context_hints keys on the bus-stamped from_agent, resolves it, and drops a non-hint sender)."""
    context_hints.clear_all()
    ok = context_hints.push("claude", "k", "treat as authoritative", from_agent=NEWBORN)
    assert not ok, "quarantined hint injection refused (can_send_kind('hint') is False)"
    assert context_hints.drain("claude") == [], "nothing folded from a quarantined sender"


def test_newborn_cannot_forge_ledger_update_kind():
    assert not resolve(NEWBORN).can_send_kind("ledger_update"), \
        "control-plane kind is conductor-only; a stranger cannot forge task-state"


# ---- N4c: the ack door refuses the stranger three independent ways -----------

def test_newborn_ack_refused_as_quarantined():
    """ack_verdict refuses a quarantined acker BEFORE it even looks at addressee -- the
    stranger cannot settle any ask, real or invented."""
    allowed, reason = ack_verdict(NEWBORN, "1783000000000-0")
    assert not allowed and "quarantined" in reason, \
        "quarantined id refused at the ack door (the first gate, before promoted-record lookup)"


def test_bootstrap_floor_still_quarantines_the_stranger():
    """Even if acl.json were lost/corrupt (resolve falls back to BOOTSTRAP_ROLES), the newborn
    is NOT a bootstrap agent -> still quarantined. The stranger has no privileged floor."""
    from core.trust.registry import _bootstrap_or_quarantine
    assert _bootstrap_or_quarantine(NEWBORN).role == "quarantined", \
        "a lost ACL file grants the stranger nothing (only core agents have a bootstrap floor)"


# ---- F4 (drill-1 review finding, deepseek): the ToolBox bus doors themselves enforce the
# ACL, not just a hardcoded kind allowlist. Before this fix a runner launched AS a quarantined
# id could chat/nudge/steer/hint through the ToolBox -- the send-side hole RB-1 left open
# (RB-1 gated only the receive/fold side). These pins build a real ToolBox bound to the
# stranger id and assert every bus door refuses BEFORE touching Redis. -------------------

def _newborn_toolbox():
    import os as _os
    from pathlib import Path
    sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "scripts"))
    from deepseek_chat import ToolBox
    return ToolBox(Path("."), allow_exec=False, trust=False, allow_secrets=False,
                   confirm=lambda _p: False, agent_id=NEWBORN, allow_write=False)


def test_toolbox_send_refuses_quarantined_before_redis():
    tb = _newborn_toolbox()
    for kind in ("chat", "note", "request", "handoff"):
        out = tb.bifrost_send("claude", "let me in", kind)
        assert out.startswith("ERROR:") and "deny-by-default" in out, \
            f"ToolBox bifrost_send({kind}) from a quarantined id must be refused, got: {out!r}"


def test_toolbox_nudge_and_steer_refuse_quarantined():
    tb = _newborn_toolbox()
    for door, txt in ((tb.bifrost_nudge, "wake up"), (tb.bifrost_steer, "change course")):
        out = door("claude", txt)
        assert out.startswith("ERROR:") and ("capability" in out or "deny-by-default" in out), \
            f"quarantined {door.__name__} must be refused at the door, got: {out!r}"


def test_toolbox_hint_send_refuses_quarantined():
    """Defense-in-depth: RB-1 already drops the hint at the FOLD door; now the SEND door
    refuses it too, so a quarantined id cannot even emit it."""
    out = _newborn_toolbox().bifrost_hint("claude", "k", "authoritative")
    assert out.startswith("ERROR:") and "deny-by-default" in out, \
        f"quarantined bifrost_hint must be refused at the send door, got: {out!r}"


def test_toolbox_admin_still_allowed_through_acl_gate():
    """The gate must NOT break the live fleet: deepseek (admin) passes the ACL check and is
    stopped only by the Redis/offline guard, never by deny-by-default. _bus is stubbed to None
    so the test asserts the GATE verdict without emitting a real message on the shared bus."""
    import os as _os
    from pathlib import Path
    sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "scripts"))
    from deepseek_chat import ToolBox
    tb = ToolBox(Path("."), allow_exec=False, trust=False, allow_secrets=False,
                 confirm=lambda _p: False, agent_id="deepseek", allow_write=False)
    tb._bus = lambda: None    # never touch the real bus -- we test the ACL verdict only
    for door in (lambda: tb.bifrost_send("claude", "x", "chat"),
                 lambda: tb.bifrost_nudge("claude", "x"),
                 lambda: tb.bifrost_steer("claude", "x"),
                 lambda: tb.bifrost_hint("claude", "k", "v")):
        out = door()
        assert "deny-by-default" not in out and "capability" not in out, \
            f"admin must pass the ACL gate (only the offline guard may stop it): {out!r}"
        assert "not on a Bifrost bus" in out, "admin reached _bus() past the gate (stubbed offline here)"
