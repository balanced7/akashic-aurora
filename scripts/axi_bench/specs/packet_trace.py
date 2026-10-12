"""AXI bench spec: `packet-trace` -- which lane the static router picks for one packet kind (no send)."""

VERB = "packet-trace"
SEED: list = []  # the route table is static policy: nothing to seed
RUNS = {
    "handoff": ["packet-trace", "handoff"],
    "narration": ["packet-trace", "narration"],
    "unknown": ["packet-trace", "bogus_kind"],
}
EMPTY = None  # a route lookup always answers; an unmapped kind is part of the answer
QUESTIONS = [
    {"run": "handoff", "q": "Which lane does a handoff packet route to?", "a": "work", "grade": "contains"},
    {"run": "narration", "q": "Which lane does a narration packet route to?", "a": "trace", "grade": "contains"},
    {"run": "handoff", "q": "Which rule decided the route?", "a": "kind:handoff", "grade": "exact"},
    {"run": "unknown", "q": "Does the router have a lane mapped for bogus_kind? Answer yes or no.", "a": "no",
     "grade": "exact"},
    {"run": "handoff", "q": "Does this route decision change how messages are delivered today? Answer yes or no.",
     "a": "no", "grade": "exact"},
]  # fmt: skip
