"""
Capability tokens + role templates -- the atomic vocabulary of the security schema.

A Grant carries a SET of these Caps (plus a path_scope for WRITE and a kind allowlist for BUS_SEND).
Roles are just named default bundles (ROLE_TEMPLATES); an agent's effective grant may add/remove caps
on top of its role. Deny-by-default: absence of a cap = the action is refused at the door.
"""
from __future__ import annotations

from enum import Enum


class Cap(str, Enum):
    """Atomic permissions. `str` base so a Cap serializes as its value in JSON."""
    READ          = "read"           # read_file, list_directory, find_files, search_files
    WRITE         = "write"          # write_file, edit_file (ALWAYS path-scoped)
    EXEC          = "exec"           # run_command
    BUS_SEND      = "bus.send"       # bifrost_send (kind-scoped via bus_send_kinds)
    BUS_NUDGE     = "bus.nudge"      # bifrost_nudge (hard interrupt)
    BUS_STEER     = "bus.steer"      # bifrost_steer (soft steer)
    ADMIN_GRANT   = "admin.grant"    # grant/revoke capabilities to others (super-admin only)
    ADMIN_APPROVE = "admin.approve"  # approve escalation requests
    KB_RECALL     = "kb.recall"      # knowledge_recall, knowledge_boot (read the KB)
    KB_LEARN      = "kb.learn"       # agent_cli.py learn (write the KB)
    NET           = "net"            # web_search
    GIT_READ      = "git.read"       # git_log, git_diff, git_show, git_status
    BIFROST_INBOX = "bifrost.inbox"  # read own inbox
    # --- screenspace tiers (T386 sec.3). DELIBERATELY IN NO ROLE TEMPLATE BELOW: these are
    # granted per seat with a time box, never inherited. The design's rule is "read-only stays
    # default, only authenticated daniil may request privileged profile", so even super_admin
    # must be granted them explicitly -- see tests/test_the_actuator_refuses_before_it_acts.py.
    # The tiers are separable on purpose: a seat may hold OBSERVE+TYPE without LAUNCH or ACT,
    # because "read the screen" and "click the irreversible button" are different trusts.
    SCREEN_OBSERVE    = "screen.observe"     # peek/refs/delta/read_text -- the shipped half
    SCREEN_FOCUS      = "screen.focus"       # raise/activate a window (steals the operator's focus)
    SCREEN_TYPE       = "screen.type"        # dispatch keystrokes into the foreground window
    SCREEN_ACT        = "screen.act"         # invoke a control (click/submit) -- irreversible
    SCREEN_LAUNCH     = "screen.launch"      # start a process / open a new session
    SCREEN_PRIVILEGED = "screen.privileged"  # act on elevated windows (UIPI boundary)


ALL_CAPS = frozenset(c for c in Cap)

#: The tiers that CHANGE the operator's machine, as opposed to observing it. Kept as a named
#: set so the fail-closed pin and the act() door agree on one definition rather than two lists
#: drifting apart (the two-surfaces defect: a guard and its guarded path must share a source).
SCREEN_WRITE_CAPS = frozenset({Cap.SCREEN_FOCUS, Cap.SCREEN_TYPE, Cap.SCREEN_ACT,
                               Cap.SCREEN_LAUNCH, Cap.SCREEN_PRIVILEGED})


def cap(value) -> Cap | None:
    """Parse a string (or Cap) to a Cap, or None if unknown -- unknown caps are ignored, never fatal."""
    if isinstance(value, Cap):
        return value
    try:
        return Cap(str(value))
    except ValueError:
        return None


def caps_from(values) -> set:
    """A set[Cap] from an iterable of strings/Caps, silently dropping unknowns."""
    return {c for c in (cap(v) for v in (values or [])) if c is not None}


# Named default bundles. An agent provisioned with a role gets these unless overridden.
ROLE_TEMPLATES: dict[str, dict] = {
    "super_admin": {
        "caps": {Cap.READ, Cap.WRITE, Cap.EXEC, Cap.BUS_SEND, Cap.BUS_NUDGE, Cap.BUS_STEER,
                 Cap.ADMIN_GRANT, Cap.ADMIN_APPROVE, Cap.KB_RECALL, Cap.KB_LEARN, Cap.NET,
                 Cap.GIT_READ, Cap.BIFROST_INBOX},
        "path_scope": ["*"],
        "bus_send_kinds": None,                       # None = every kind
    },
    "admin": {
        # trust-but-verify: full read+write, but NO exec and NO admin.grant (must escalate for those)
        "caps": {Cap.READ, Cap.WRITE, Cap.BUS_SEND, Cap.BUS_NUDGE, Cap.BUS_STEER,
                 Cap.KB_RECALL, Cap.KB_LEARN, Cap.NET, Cap.GIT_READ, Cap.BIFROST_INBOX},
        "path_scope": ["*"],
        "bus_send_kinds": {"chat", "note", "request", "reply", "nudge", "steer", "inform"},
    },
    "member": {
        "caps": {Cap.READ, Cap.BUS_SEND, Cap.KB_RECALL, Cap.GIT_READ, Cap.BIFROST_INBOX},
        "path_scope": [],                             # no write
        "bus_send_kinds": {"chat", "note"},           # chat/note only -- no handoff/nudge/request
    },
    "restricted": {
        # fleet one-shot models: read the KB, nothing else
        "caps": {Cap.KB_RECALL},
        "path_scope": [],
        "bus_send_kinds": set(),                       # no bus send
    },
    "quarantined": {
        # brand-new / unverified agent: read + read-own-inbox only. Fail-closed default.
        "caps": {Cap.READ, Cap.BIFROST_INBOX},
        "path_scope": [],
        "bus_send_kinds": set(),
    },
}

DEFAULT_ROLE = "quarantined"    # what an unknown/unverified agent resolves to (deny-by-default)
