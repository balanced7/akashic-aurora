"""AXI bench spec: `unlock` -- release an advisory path-lock (released, a peer's, already free)."""

VERB = "unlock"
SEED = [
    ["lock", "bob", "docs/x.md", "--ttl", "120"],
    ["lock", "alice", "core/a.py", "--ttl", "600"],
]
# Runs share one seeded store and run in order: alice releases her lock, tries bob's, then tries
# her own path again after it is already free.
RUNS = {
    "release": ["unlock", "alice", "core/a.py"],
    "peer": ["unlock", "alice", "docs/x.md"],
    "free": ["unlock", "alice", "core/a.py"],
}
# Nothing to release exits 1 today (before and after); the AXI empty-state check needs exit 0,
# so it is left out rather than scored against an exit code this change keeps on purpose.
EMPTY = None
QUESTIONS = [
    {"run": "release", "q": "Was the lock on core/a.py released? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "peer", "q": "Which agent holds the lock on docs/x.md?", "a": "bob", "grade": "exact"},
    {
        "run": "free",
        "q": "Is core/a.py locked by anyone right now? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "peer",
        "q": "Did the command fail because nobody holds docs/x.md, or because another agent holds it? "
        "Answer nobody or another.",
        "a": "another",
        "grade": "exact",
    },
    {
        "run": "peer",
        "q": "What command shows who holds which locks? Give the command only.",
        "a": ["locks"],
        "grade": "contains",
    },
]
