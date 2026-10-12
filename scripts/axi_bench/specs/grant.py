"""AXI bench spec: `grant` -- mint, revoke and list ACL grants, against a throwaway ACL.

The ACL lives in security/acl.json unless AKASHIC_ACL_PATH says otherwise, and the sandbox reset
does not touch it. So this module writes a temporary ACL holding one super-admin (`boss`, the
granter every seed and run names) when it is loaded and points AKASHIC_ACL_PATH at it; every run
inherits that. The seeds are idempotent (a grant replaces the agent's previous one), so the
second side starts from the same grants; the revoke run's grant is re-seeded before it.
"""

import json
import os
import tempfile
from pathlib import Path

_acl = Path(tempfile.mkdtemp(prefix="axi-grant-")) / "acl.json"
_acl.write_text(
    json.dumps(
        {
            "grants": [
                {
                    "agent_id": "boss",
                    "role": "super_admin",
                    "caps": ["admin.approve", "admin.grant", "bifrost.inbox", "bus.nudge", "bus.send", "bus.steer",
                             "exec", "git.read", "kb.learn", "kb.recall", "net", "read", "write"],
                    "path_scope": ["*"],
                    "granted_by": "operator",
                    "granted_at": "2026-10-01T00:00:00Z",
                    "expires_at": None,
                    "reason": "bench super-admin",
                }
            ]
        }
    ),
    encoding="utf-8",
)  # fmt: skip
os.environ["AKASHIC_ACL_PATH"] = str(_acl)

VERB = "grant"
SEED = [
    ["grant", "alice", "--role", "member", "--by", "boss", "--reason", "bench seat for tests", "--hours", "24"],
    ["grant", "bob", "--role", "restricted", "--by", "boss", "--reason", "read-only helper", "--permanent"],
    ["grant", "carol", "--role", "member", "--by", "boss", "--reason", "one-day pairing", "--hours", "8"],
]
RUNS = {
    "list": ["grant"],
    "dry": ["grant", "dave", "--role", "member", "--by", "boss", "--reason", "trial", "--hours", "4", "--dry-run"],
    "refused": ["grant", "dave", "--role", "member", "--by", "alice", "--reason", "trial", "--hours", "1"],
    "revoke": ["grant", "carol", "--revoke", "--by", "boss", "--reason", "pairing over"],
}
EMPTY = None  # the ACL is outside the sandbox reset, so there is no empty run to make
QUESTIONS = [
    {"run": "list", "q": "How many grants are stored?", "a": 4, "grade": "number"},
    {"run": "list", "q": "Which role does bob hold?", "a": "restricted", "grade": "exact"},
    {
        "run": "list",
        "q": "Which agents hold permanent grants? List them separated by commas.",
        "a": ["bob", "boss"],
        "grade": "set",
    },
    {"run": "list", "q": "Who granted alice her role?", "a": "boss", "grade": "exact"},
    {"run": "dry", "q": "Was anything written? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "refused", "q": "Did the grant succeed? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "revoke", "q": "Which role did carol hold before this command?", "a": "member", "grade": "exact"},
]
