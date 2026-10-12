"""AXI bench spec: `toast` -- thank a peer, with the lesson that helped as the receipt.

The receipt is checked against the learning store (seeded here, in the sandbox db); the bus
message and the note also land in the sandbox (Redis db and AI_SETUP), never the live store.
"""

VERB = "toast"
SEED = [
    ["learn", "alice", "--experiment", "port_clash", "--tried", "ran the suite", "--result", "hung at start",
     "--recommend", "Check that port 16379 is free first.", "--category", "performance", "--success", "yes"],
]  # fmt: skip
RUNS = {
    "ok": ["toast", "bench", "alice", "port_clash", "--credit", "saved two hours of bisecting"],
    "forced": ["toast", "bench", "alice", "made_up_thing", "--credit", "thanks anyway", "--force"],
    "refused": ["toast", "bench", "alice", "made_up_thing", "--credit", "thanks anyway"],
    "wrong_owner": ["toast", "bench", "carol", "port_clash", "--credit", "thanks"],
    "no_credit": ["toast", "bench", "alice", "port_clash"],
}
EMPTY = None
QUESTIONS = [
    {"run": "ok", "q": "Was the receipt verified? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "ok", "q": "Was the bus message sent? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "forced", "q": "What verification tier is the toast labelled with?", "a": "GUESS", "grade": "exact"},
    {"run": "refused", "q": "Was the toast sent? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "wrong_owner", "q": "Which agent does the port_clash lesson belong to?", "a": "alice", "grade": "exact"},
    {"run": "no_credit", "q": "Which flag must be added for the command to work? Give the flag only.",
     "a": ["--credit"], "grade": "contains"},
]  # fmt: skip
