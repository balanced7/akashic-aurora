"""AXI bench spec: `status` -- is the store up, and how much is in it."""

VERB = "status"
SEED = [
    ["learn", "bench", "--experiment", "e1", "--tried", "a", "--result", "b"],
    ["learn", "bench", "--experiment", "e2", "--tried", "a", "--result", "b"],
    ["learn", "bench", "--experiment", "e3", "--tried", "a", "--result", "b"],
]
RUNS = {"status": ["status"]}
EMPTY = ["status"]
QUESTIONS = [
    {"run": "status", "q": "How many lessons are stored in memory?", "a": 3, "grade": "number"},
    {"run": "status", "q": "Is Redis reachable? Answer yes or no.", "a": "yes", "grade": "exact"},
    {
        "run": "status",
        "q": "Does the narrative spine report any errors? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {"run": "status", "q": "How many agent memory keys are there?", "a": 0, "grade": "number"},
]
