"""AXI bench spec: `capture` -- full-fidelity read of bus messages from the inbox streams."""

PLAN = (
    "Migration plan:\n1. freeze writes\n2. copy the tables\n3. flip the reader to the new store\nRollback: flip back."
)

VERB = "capture"
SEED = [
    ["bifrost-send", "alice", PLAN, "--to", "bench", "--kind", "handoff", "--expect-reply-within", "0"],
    ["bifrost-send", "alice", "second note: the copy step takes about 40 minutes", "--to", "bench"],
    ["bifrost-send", "bob", "unrelated chatter", "--to", "bench"],
]  # fmt: skip
RUNS = {
    "alice": ["capture", "--from-agent", "alice", "--count", "5"],
    "persist": ["capture", "--from-agent", "bob", "--persist", "/dev/null"],
    "miss": ["capture", "9999999999999-0"],
    "usage": ["capture"],
}
EMPTY = None  # a capture names what to read: it resolves or it is a NOT_FOUND error
QUESTIONS = [
    {"run": "alice", "q": "How many messages from alice were captured?", "a": 2, "grade": "number"},
    {"run": "alice", "q": "What is step 3 of the migration plan?", "a": ["flip", "reader"], "grade": "contains"},
    {"run": "alice", "q": "How long does the copy step take, in minutes?", "a": 40, "grade": "number"},
    {"run": "persist", "q": "How many characters were persisted?", "a": len("unrelated chatter"), "grade": "number"},
    {"run": "miss", "q": "Was the requested message found? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "usage",
        "q": "What flag reads the newest messages from one sender instead of a stream id? Give the flag only.",
        "a": "--from-agent",
        "grade": "contains",
    },
]
