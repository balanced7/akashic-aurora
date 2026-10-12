"""AXI bench spec: `locks` -- who holds which advisory path-locks."""

VERB = "locks"
SEED = [
    ["lock", "alice", "core/a.py", "--ttl", "600"],
    ["lock", "bob", "docs/x.md", "--ttl", "120"],
    ["lock", "alice", "scripts/y.py", "--ttl", "600"],
]
RUNS = {"list": ["locks"]}
EMPTY = ["locks"]
QUESTIONS = [
    {"run": "list", "q": "Which agent holds the lock on docs/x.md?", "a": "bob", "grade": "exact"},
    {"run": "list", "q": "How many locks are held in total?", "a": 3, "grade": "number"},
    {
        "run": "list",
        "q": "Which paths does alice hold locks on? List them separated by commas.",
        "a": ["core/a.py", "scripts/y.py"],
        "grade": "set",
    },
    {"run": "list", "q": "What is the TTL, in seconds, of the lock on docs/x.md?", "a": 120, "grade": "number"},
    {"run": "list", "q": "Does carol hold any lock? Answer yes or no.", "a": "no", "grade": "exact"},
]
