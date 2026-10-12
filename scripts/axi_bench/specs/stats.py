"""AXI bench spec: `stats` -- the recall-value funnel, and the --silence denominator."""

VERB = "stats"
SEED = [
    ["learn", "bench", "--experiment", "port_clash", "--tried", "a", "--result", "b"],
    ["learn", "bench", "--experiment", "git_blanket_staging", "--tried", "a", "--result", "b"],
    ["learn", "bench", "--experiment", "token_refresh", "--tried", "a", "--result", "b"],
    ["learn", "bench", "--repeat-of", "git_blanket_staging", "--tried", "ran git add -A again"],
]
RUNS = {"funnel": ["stats"], "silence": ["stats", "--silence"]}
EMPTY = ["stats"]
QUESTIONS = [
    {"run": "funnel", "q": "How many lessons are in the corpus?", "a": 3, "grade": "number"},
    {"run": "funnel", "q": "How many repeats (a lesson violated again) are recorded?", "a": 1, "grade": "number"},
    {
        "run": "funnel",
        "q": "Which lesson was violated again? Give its name only.",
        "a": "git_blanket_staging",
        "grade": "exact",
    },
    # The --silence numbers come from the recall state directory, which this branch's bench
    # sandbox does not redirect; questions on that run ask only what does not depend on them.
    {
        "run": "silence",
        "q": "What is the full command to run the pack replay? Give the command only.",
        "a": ["-m core.recall.pack_replay"],
        "grade": "contains",
    },
    {
        "run": "silence",
        "q": "Over how many hours is this silence window measured?",
        "a": 24,
        "grade": "number",
    },
]
