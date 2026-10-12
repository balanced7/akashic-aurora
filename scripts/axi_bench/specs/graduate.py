"""AXI bench spec: `graduate` -- retire a lesson from recall because automation enforces its rule.

The runs share one store in order: graduate, then undo a second lesson's graduation, then the two
errors (no such lesson; nothing said about the enforcing automation).
"""

VERB = "graduate"
SEED = [
    ["learn", "alice", "--experiment", "blanket_staging", "--tried", "a", "--result", "b",
     "--recommend", "Use when staging: name each path."],
    ["learn", "alice", "--experiment", "tab_width", "--tried", "a", "--result", "b",
     "--recommend", "Use when formatting: four spaces."],
    ["graduate", "alice", "--experiment", "tab_width", "--enforced-by", "ruff format"],
]  # fmt: skip
RUNS = {
    "grad": ["graduate", "bench", "--experiment", "blanket_staging", "--enforced-by", "pre-commit hook"],
    "undo": ["graduate", "bench", "--experiment", "tab_width", "--undo"],
    "missing": ["graduate", "bench", "--experiment", "no_such_lesson", "--enforced-by", "ci"],
    "usage": ["graduate", "bench", "--experiment", "blanket_staging"],
}
EMPTY = None
QUESTIONS = [
    {"run": "grad", "q": "What automation now enforces the graduated lesson?", "a": "pre-commit hook",
     "grade": "contains"},
    {"run": "grad", "q": "Will the graduated lesson still take recall slots? Answer yes or no.", "a": "no",
     "grade": "exact"},
    {"run": "undo", "q": "Does tab_width compete for recall slots again? Answer yes or no.", "a": "yes",
     "grade": "exact"},
    {"run": "missing", "q": "Did the command succeed? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "missing", "q": "What command lists the lesson names to check the spelling? Give the command only.",
     "a": ["list"], "grade": "contains"},
    {"run": "usage", "q": "Which flag is missing from the command?", "a": ["--enforced-by"], "grade": "contains"},
]  # fmt: skip
