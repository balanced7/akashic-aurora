"""AXI bench spec: `promoted` -- durable salient bus messages (handoffs, decisions, ...)."""

VERB = "promoted"
SEED = [
    ["bifrost-send", "alice", "handing off the cache refactor; tests in tests/test_cache.py are green", "--to", "bob",
     "--kind", "handoff", "--expect-reply-within", "0"],
    ["bifrost-send", "carol", "decision: we ship the v2 parser on Friday", "--to", "bob", "--kind", "decision"],
    ["bifrost-send", "bob", "just chatting", "--to", "alice"],
    ["bifrost-send", "dave", "blocked on the staging database credentials", "--to", "alice", "--kind", "blocker",
     "--expect-reply-within", "0"],
]  # fmt: skip
RUNS = {"all": ["promoted"], "page": ["promoted", "--limit", "2"]}
EMPTY = ["promoted"]
QUESTIONS = [
    {"run": "all", "q": "How many durable messages are listed?", "a": 3, "grade": "number"},
    {"run": "all", "q": "Who sent the handoff, and to whom? Answer as sender,recipient.", "a": ["alice", "bob"],
     "grade": "set"},
    {"run": "all", "q": "On which day will the v2 parser ship?", "a": "friday", "grade": "exact"},
    {"run": "all", "q": "How many of these messages are unhandled? Answer with a number.", "a": 0, "grade": "number"},
    {"run": "page", "q": "Does this output show every durable message? Answer yes or no.", "a": "no",
     "grade": "exact"},
    {"run": "page", "q": "What exact command would show more of the durable messages? Give the command only.",
     "a": ["promoted", "--limit"], "grade": "contains"},
]  # fmt: skip
