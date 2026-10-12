"""AXI bench spec: `repeat` -- record that an existing lesson was violated anyway, and the report.

The runs share one store in order: the record run adds a third repeat before the report reads.
"""

VERB = "repeat"
SEED = [
    ["learn", "alice", "--experiment", "stage_paths", "--tried", "a", "--result", "b",
     "--recommend", "Use when staging files: name each path."],
    ["learn", "alice", "--experiment", "port_check", "--tried", "a", "--result", "b",
     "--recommend", "Use when tests hang: check the port."],
    ["repeat", "stage_paths", "--what", "staged everything", "--recall-outcome", "fired", "--agent", "bob"],
    ["repeat", "port_check", "--what", "skipped the check", "--recall-outcome", "silent", "--agent", "carol"],
]  # fmt: skip
RUNS = {
    "record": ["repeat", "stage_paths", "--what", "staged everything again", "--recall-outcome", "fired",
               "--agent", "bob"],
    "report": ["repeat", "--report"],
    "unknown": ["repeat", "no_such_lesson", "--what", "x"],
}  # fmt: skip
EMPTY = ["repeat", "--report"]
QUESTIONS = [
    {"run": "record", "q": "Against which lesson was the repeat recorded?", "a": "stage_paths", "grade": "exact"},
    {"run": "report", "q": "How many repeats are recorded in total?", "a": 3, "grade": "number"},
    {"run": "report", "q": "Which lesson was violated most often?", "a": "stage_paths", "grade": "exact"},
    {"run": "report", "q": "How many repeats happened while recall had fired?", "a": 2, "grade": "number"},
    {"run": "unknown", "q": "Was the repeat recorded? Answer yes or no.", "a": "no", "grade": "exact"},
]
