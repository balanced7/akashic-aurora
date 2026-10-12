"""AXI bench spec: `tag-anti-pattern` -- mark an existing lesson as a reusable known-bad."""

VERB = "tag-anti-pattern"
SEED = [
    ["learn", "alice", "--experiment", "blind_retry", "--tried", "retried in a loop", "--result", "locked out",
     "--recommend", "Use when a request fails with 401: refresh once, never loop."],
]  # fmt: skip
RUNS = {
    "tag": ["tag-anti-pattern", "bench", "--experiment", "blind_retry", "--name", "retry-loop",
            "--reason", "locks the account"],
    "missing": ["tag-anti-pattern", "bench", "--experiment", "no_such_lesson", "--name", "x"],
}  # fmt: skip
EMPTY = None
QUESTIONS = [
    {"run": "tag", "q": "Was the lesson tagged? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "tag", "q": "What anti-pattern name was given to the lesson?", "a": "retry-loop", "grade": "exact"},
    {"run": "missing", "q": "Did the command succeed? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "missing",
        "q": "Which command must be run first to create the lesson? Give the verb only.",
        "a": ["learn"],
        "grade": "contains",
    },
]
