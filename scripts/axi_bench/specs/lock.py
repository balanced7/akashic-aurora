"""AXI bench spec: `lock` -- claim an advisory path-lock (taken, refreshed, refused)."""

VERB = "lock"
SEED = [["lock", "bob", "docs/x.md", "--ttl", "120"]]
# Runs share one seeded store and run in order: alice takes core/a.py, then claims it again
# (a refresh of her own lock), then asks for bob's path and is refused.
RUNS = {
    "take": ["lock", "alice", "core/a.py", "--ttl", "600"],
    "again": ["lock", "alice", "core/a.py", "--ttl", "300"],
    "denied": ["lock", "alice", "docs/x.md"],
}
EMPTY = None  # a mutation has no empty listing; the refusal and the offline bus are its error paths
QUESTIONS = [
    {"run": "take", "q": "Did alice get the lock on core/a.py? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "take", "q": "What token number does the lock carry?", "a": 2, "grade": "number"},
    {
        "run": "again",
        "q": "Was this a brand-new lock, or a refresh of a lock alice already held? Answer new or refreshed.",
        "a": "refreshed",
        "grade": "exact",
    },
    {"run": "denied", "q": "Which agent holds the lock on docs/x.md?", "a": "bob", "grade": "exact"},
    {
        "run": "take",
        "q": "What exact command releases this lock when alice is done? Give the command only.",
        "a": ["unlock", "alice", "core/a.py"],
        "grade": "contains",
    },
]
