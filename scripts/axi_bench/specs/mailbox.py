"""AXI bench spec: `mailbox` -- what is addressed to an agent, and in what state."""

VERB = "mailbox"
SEED = [
    ["bifrost-send", "alice", "please review core/a.py", "--to", "bench", "--kind", "request",
     "--expect-reply-within", "0"],
    ["bifrost-send", "bob", "FYI build green", "--to", "bench"],
    ["bifrost-send", "carol", "which port does redis use", "--to", "bench", "--kind", "question",
     "--expect-reply-within", "0"],
    ["bifrost-sync", "bench", "--consume"],
    ["bifrost-send", "dave", "late note about the release", "--to", "bench", "--kind", "request",
     "--expect-reply-within", "0"],
    ["bifrost-send", "erin", "one more for the pile", "--to", "bench"],
]  # fmt: skip
RUNS = {"list": ["mailbox", "bench"], "none": ["mailbox", "nobody"]}
EMPTY = ["mailbox", "nobody"]
QUESTIONS = [
    {"run": "list", "q": "How many messages addressed to bench are still unhandled (not yet consumed)?", "a": 2,
     "grade": "number"},
    {"run": "list", "q": "How many messages has bench consumed?", "a": 3, "grade": "number"},
    {"run": "list", "q": "Which agents sent the unhandled messages? List them separated by commas.",
     "a": ["dave", "erin"], "grade": "set"},
    {"run": "list", "q": "What kind of message did dave send?", "a": "request", "grade": "exact"},
    {"run": "list", "q": "What command reads the full body of one of these messages? Give the command only.",
     "a": ["mailbox", "bench", "--open"], "grade": "contains"},
    {"run": "none", "q": "How many messages are addressed to nobody?", "a": 0, "grade": "number"},
]  # fmt: skip
