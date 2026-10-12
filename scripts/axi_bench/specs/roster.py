"""AXI bench spec: `roster` -- every seat's proven liveness.

A seat beats when `bifrost-sync` runs with a session id in the environment. The bench strips the
harness's own session variables, so this spec names an incarnation for the sandboxed CLI: the
harness copies os.environ into every run, and BIFROST_INCARNATION is not one of the stripped
prefixes. Each seeded agent then gets one LIVE seat, <agent>#<first 8 of the id>."""

import os

os.environ.setdefault("BIFROST_INCARNATION", "benchseat-0001")

VERB = "roster"
SEED = [
    ["bifrost-sync", "alice"],
    ["bifrost-sync", "bob"],
]
RUNS = {
    "raw": ["roster"],
    "by_agent": ["roster", "--by-agent"],
}
EMPTY = ["roster"]
QUESTIONS = [
    {"run": "raw", "q": "How many seats does the roster list?", "a": 2, "grade": "number"},
    {"run": "raw", "q": "What state is alice's seat in?", "a": "LIVE", "grade": "exact"},
    {"run": "raw", "q": "Which phase was bob's seat in at its last beat?", "a": "sync", "grade": "exact"},
    {"run": "by_agent", "q": "Is any agent churning? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "raw",
        "q": "Does this roster check whether the seat's process is actually alive? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "raw",
        "q": "What command checks the things this roster does not? Give the command only.",
        "a": ["doctor"],
        "grade": "contains",
    },
]
