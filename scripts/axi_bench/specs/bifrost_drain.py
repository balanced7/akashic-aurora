"""AXI bench spec: `bifrost-drain` -- ask one runner for a graceful exit."""

VERB = "bifrost-drain"
SEED = []
RUNS = {"drain": ["bifrost-drain", "claude", "--to", "deepseek", "--reason", "new code landed"]}
EMPTY = None
QUESTIONS = [
    {"run": "drain", "q": "Which runner was asked to drain?", "a": "deepseek", "grade": "exact"},
    {
        "run": "drain",
        "q": "After how many seconds does the request clear itself if the runner ignores it?",
        "a": 300,
        "grade": "number",
    },
    {
        "run": "drain",
        "q": "Does the runner abandon the message it is working on? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "drain",
        "q": "What should be done once the runner has exited? Answer with one verb.",
        "a": ["relaunch"],
        "grade": "contains",
    },
]
