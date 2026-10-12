"""AXI bench spec: `shell-home` -- where the shell is, and where fresh harness shells land.

Only the read path: --set and --clear write harness settings, so they stay out of the bench
even though each run has a throwaway HOME."""

VERB = "shell-home"
SEED: list = []
RUNS = {"read": ["shell-home"]}
EMPTY = ["shell-home"]
QUESTIONS = [
    {"run": "read", "q": "Is a shell home mapping set? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "read", "q": "Is the profile hook installed? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "read", "q": "Is this shell a harness shell? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "read",
        "q": "Where do fresh harness shells land right now? Answer in a few words.",
        "a": ["launch"],
        "grade": "contains",
    },
    {
        "run": "read",
        "q": "What is the full command to map fresh harness shells to a directory? Give the command only.",
        "a": ["shell-home --set"],
        "grade": "contains",
    },
]
