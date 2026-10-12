"""AXI bench spec: `learn` -- record a lesson; the confirmation and its warnings."""

VERB = "learn"
SEED = [
    ["learn", "bench", "--experiment", "port_clash", "--tried", "ran the suite", "--result", "hung at start",
     "--recommend", "Use when tests hang at start: check that port 16379 is free first.", "--category",
     "performance", "--success", "yes"],
]  # fmt: skip
RUNS = {
    "related": ["learn", "alice", "--experiment", "port_clash_again", "--tried", "ran the suite", "--result",
                "hung at start", "--recommend", "Use when tests hang at start: check port 16379 is free.",
                "--category", "performance", "--success", "no"],
    "missing": ["learn", "alice", "--tried", "something"],
}  # fmt: skip
EMPTY = None  # a write verb: there is no empty listing to state
QUESTIONS = [
    {"run": "related", "q": "Was the lesson recorded? Answer yes or no.", "a": "yes", "grade": "exact"},
    {
        "run": "related",
        "q": "Which existing lesson does the new lesson overlap with? Give its name only.",
        "a": "port_clash",
        "grade": "exact",
    },
    {
        "run": "related",
        "q": "On how many of the 5 dimensions does it overlap that lesson?",
        "a": 3,
        "grade": "number",
    },
    {
        "run": "related",
        "q": "What exact command would tag this failure as a known anti-pattern? Give the command only.",
        "a": ["tag-anti-pattern alice", "--experiment port_clash_again"],
        "grade": "contains",
    },
    {"run": "missing", "q": "Was a lesson recorded? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "missing",
        "q": "Which flag must be added for the command to work? Give the flag only.",
        "a": ["--experiment"],
        "grade": "contains",
    },
]
