"""AXI bench spec: `seat-identity` -- which seat id this session resolves to, and from where.

Bindings are files in tempfile.gettempdir(), outside the sandbox, so this spec points TMPDIR at
a directory of its own for the sandboxed CLI (the harness copies os.environ into every run) and
uses session ids no real session has. The bench sets AKASHIC_AGENT_ID=bench, so an unbound
session resolves from the env."""

import os
import tempfile

os.environ["TMPDIR"] = tempfile.mkdtemp(prefix="axi-bench-seat-")

VERB = "seat-identity"
SEED = [["seat-identity", "alice", "--session", "bench-sess-0001"]]
# Runs share the seeded binding and run in order; `clear` comes last because it removes it.
RUNS = {
    "show": ["seat-identity", "--session", "bench-sess-0001"],
    "env": ["seat-identity", "--session", "bench-sess-0002"],
    "nosession": ["seat-identity"],
    "clear": ["seat-identity", "--session", "bench-sess-0001", "--clear"],
}
EMPTY = ["seat-identity", "--session", "bench-sess-0009"]
QUESTIONS = [
    {"run": "show", "q": "Which seat id does this session resolve to?", "a": "alice", "grade": "exact"},
    {
        "run": "show",
        "q": "Where did the identity come from? Answer binding, env or unknown.",
        "a": "binding",
        "grade": "exact",
    },
    {
        "run": "env",
        "q": "Is this identity bound to this session specifically? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "env",
        "q": "What exact command binds this session to its seat id? Give the command only.",
        "a": ["seat-identity", "bench", "--session bench-sess-0002"],
        "grade": "contains",
    },
    {"run": "nosession", "q": "Did the command succeed? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "clear", "q": "Was a binding removed? Answer yes or no.", "a": "yes", "grade": "exact"},
]
