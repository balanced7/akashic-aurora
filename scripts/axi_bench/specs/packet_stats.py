"""AXI bench spec: `packet-stats` -- the shadow router's bounded decision and mirror counters."""

VERB = "packet-stats"
SEED = [
    ["bifrost-send", "alice", "one", "--to", "bob"],
    ["bifrost-send", "alice", "two", "--to", "bob"],
    ["bifrost-send", "bob", "three", "--to", "alice"],
    ["bifrost-send", "carol", "take the parser", "--to", "dave", "--kind", "handoff", "--expect-reply-within", "0"],
    ["bifrost-send", "dave", "review a.py", "--to", "carol", "--kind", "request", "--expect-reply-within", "0"],
]  # fmt: skip
RUNS = {"stats": ["packet-stats"]}
EMPTY = ["packet-stats"]
QUESTIONS = [
    {"run": "stats", "q": "How many routing decisions were recorded for chat packets?", "a": 3, "grade": "number"},
    {"run": "stats", "q": "How many routing decisions were recorded in total, across all kinds?", "a": 5,
     "grade": "number"},
    {"run": "stats", "q": "How many handoff packets were mirrored successfully?", "a": 1, "grade": "number"},
    {"run": "stats", "q": "How many mirror failures were recorded? Answer with a number.", "a": 0, "grade": "number"},
    {"run": "stats", "q": "Does the stored policy match the current policy? Answer yes or no.", "a": "yes",
     "grade": "exact"},
]  # fmt: skip
