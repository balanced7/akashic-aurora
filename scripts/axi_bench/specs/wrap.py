"""AXI bench spec: `wrap` -- the session draft, and the guard that protects a hand-written note."""

VERB = "wrap"
SEED = [
    ["learn", "bench", "--experiment", "port_clash", "--tried", "ran the suite", "--result", "hung",
     "--recommend", "Use when tests hang at start: check that port 16379 is free first."],
    # a hand-written where-we-are: `wrap --commit` must refuse to overwrite it
    ["note", "bench", "--title", "where-we-are", "--note", "Wave 3 done; next: the ledger table."],
]  # fmt: skip
RUNS = {"draft": ["wrap"], "guard": ["wrap", "--commit"]}
EMPTY = ["wrap"]
QUESTIONS = [
    {
        "run": "draft",
        "q": "Has this draft already been recorded as a note? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {"run": "draft", "q": "How many lessons from this session does the draft draw on?", "a": 1, "grade": "number"},
    {
        "run": "draft",
        "q": "What exact command records this draft as the where-we-are note? Give the command only.",
        "a": ["wrap --commit"],
        "grade": "contains",
    },
    {"run": "guard", "q": "Was a note written by this command? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "guard",
        "q": "Which flag makes wrap overwrite the hand-written note anyway? Give the flag only.",
        "a": ["--force"],
        "grade": "contains",
    },
]
