"""AXI bench spec: `ground` -- typed evidence for verb:<name>, or a seat's continuity profile."""

VERB = "ground verb:recall"  # the unknown-flag check needs a complete command: target is required
SEED = [
    ["learn", "bench", "--experiment", "port_clash", "--tried", "a", "--result", "b", "--recommend",
     "check port 16379"],
    ["learn", "bench", "--experiment", "cache_fix", "--tried", "a", "--result", "b"],
    ["handoff", "alice", "--to", "bench", "--task", "finish the AXI batch"],
]  # fmt: skip
RUNS = {
    "verb": ["ground", "verb:recall"],
    "seat": ["ground", "seat:bench", "--continuity"],
    "bad": ["ground", "seat:bench"],
}
EMPTY = ["ground", "seat:bench", "--continuity"]
QUESTIONS = [
    {"run": "verb", "q": "What is the state of the EXERCISED rung? Give one word.", "a": "partial", "grade": "exact"},
    {"run": "verb", "q": "How many blind spots does the result report?", "a": 2, "grade": "number"},
    {"run": "seat", "q": "How many lessons by this seat were observed?", "a": 2, "grade": "number"},
    {"run": "seat", "q": "Was an identity verdict computed? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "seat", "q": "Who handed work to this seat?", "a": "alice", "grade": "exact"},
    {
        "run": "bad",
        "q": "What must be added to the command for seat grounding to run? Give the flag only.",
        "a": ["--continuity"],
        "grade": "contains",
    },
]
