"""AXI bench spec: `bifrost-pause` -- freeze the bus auto-responders, hard or soft."""

VERB = "bifrost-pause"
SEED = []
RUNS = {
    "hard": ["bifrost-pause", "--reason", "operator barge-in", "--ttl", "600"],
    "soft": ["bifrost-pause", "--reason", "wind down", "--soft"],
}
EMPTY = None
QUESTIONS = [
    {"run": "hard", "q": "Is in-flight work abandoned by this pause? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "hard", "q": "After how many seconds does the pause clear itself?", "a": 600, "grade": "number"},
    {"run": "soft", "q": "Is in-flight work abandoned by this pause? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "soft",
        "q": "Does this pause clear itself after a time limit? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "hard",
        "q": "What command ends the pause? Give the command only.",
        "a": ["bifrost-resume"],
        "grade": "contains",
    },
]
