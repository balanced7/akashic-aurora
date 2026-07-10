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
