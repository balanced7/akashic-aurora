"""AXI bench spec: usage errors -- a mistyped flag and a mistyped verb (AXI section 6)."""

VERB = "locks"
SEED = []
RUNS = {
    "bad_flag": ["locks", "--stat"],
    "bad_verb": ["lokcs"],
}
EMPTY = None
QUESTIONS = [
    {"run": "bad_flag", "q": "Did the command succeed? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "bad_flag",
        "q": "Which flags does the locks command accept? List them separated by commas.",
        "a": ["--json", "--help"],
        "grade": "set",
    },
    {"run": "bad_flag", "q": "Which argument was not recognized?", "a": "--stat", "grade": "exact"},
    {
        "run": "bad_verb",
        "q": "Which existing command did the user most likely mean? Give the command name only.",
        "a": "locks",
        "grade": "exact",
    },
]
