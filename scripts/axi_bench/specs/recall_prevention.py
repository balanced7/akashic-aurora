"""AXI bench spec: `recall-prevention` -- what recall prevented, read from the outcome stage log.

The stage log is written only by the harness hooks when an action resolves, so no CLI verb can
seed it: the bench sees an empty stage log beside one repeat filed through the CLI. That is the
honest offline picture.
"""

VERB = "recall-prevention"
SEED = [
    ["learn", "alice", "--experiment", "stage_paths", "--tried", "a", "--result", "b",
     "--recommend", "Use when staging files: name each path."],
    ["repeat", "stage_paths", "--what", "staged everything again", "--recall-outcome", "fired",
     "--agent", "bob"],
]  # fmt: skip
RUNS = {"report": ["recall-prevention"]}
EMPTY = ["recall-prevention"]
QUESTIONS = [
    {"run": "report", "q": "How many stage rows did the report read?", "a": 0, "grade": "number"},
    {"run": "report", "q": "How many prevention candidates are there?", "a": 0, "grade": "number"},
    {"run": "report", "q": "What is the coverage, as a number?", "a": 0, "grade": "number"},
    {"run": "report", "q": "How many observations were VIOLATED?", "a": 0, "grade": "number"},
    {
        "run": "report",
        "q": "Does this report change lesson rankings or credit? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
]
