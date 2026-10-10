"""kinds -- the bridge allowlist: the only message kinds that may cross a fleet boundary.

One allowlist for every path out of the fleet: the old HMAC bridge (`remote_relay` re-exports it),
the link exporter, and the Rust daemon, whose copy (`aurora-rs/link/src/acl.rs`, BRIDGE_KINDS) a
test pins to this set. No control kind (halt, nudge, steer, interrupt) crosses, now or later.
"""

from __future__ import annotations

#: This list answers "is this safe to accept from ANOTHER FLEET?" -- a different question from
#: "may a phone see it?", which is why it is not shared with the Discord forward list. A pin
#: (test_bridge_allowlist_contains_no_control_kind) fails red the moment a control verb appears.
BRIDGE_KINDS = frozenset(
    {
        "chat",
        "question",
        "handoff",
        "reply",
        "completion",
        "blocker",
        "note",
    }
)
