"""AXI bench spec: `episode` -- session bookends: the open episode, close with a draft, accept."""

VERB = "episode current"  # the unknown-flag check needs a complete command: action is required
SEED = [
    ["episode", "current"],  # opens the episode the beats below land in
    ["log", "action", "--summary", "fixed the port clash in tests", "--source", "bench:fix"],
    ["log", "note", "--summary", "renamed the config loader", "--source", "bench:note"],
]
RUNS = {
    "current": ["episode", "current"],
    "close": ["episode", "close"],
    "accept_missing": ["episode", "accept", "ch_does_not_exist", "--title", "x"],
}
EMPTY = ["episode", "current"]
QUESTIONS = [
    {"run": "current", "q": "How many beats are in the current episode?", "a": 2, "grade": "number"},
    {
        "run": "current",
        "q": "Does the current episode have a title yet? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "current",
        "q": "What is the full command to close this episode and draft its title? Give the command only.",
        "a": ["episode close"],
        "grade": "contains",
    },
    {
        "run": "close",
        "q": "What title was drafted for the closed episode?",
        "a": "fixed the port clash in tests",
        "grade": "exact",
    },
    {
        "run": "close",
        "q": "What is the full command to finalize the episode that was just closed? Give the command only.",
        "a": ["episode accept ch_"],
        "grade": "contains",
    },
    {
        "run": "accept_missing",
        "q": "Did finalizing the episode succeed? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
]
