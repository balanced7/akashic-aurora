"""AXI bench spec: `memreplay` -- the memory replay queue and snapshots, offline paths only.

`memreplay run` and `drain` replay scenarios with real models, so they only run here without
the flags they require, which they refuse before doing anything. The queue fills the way it
does in use: recording a lesson queues it ("new"), and a later change keeps the first record."""

VERB = "memreplay"
SEED = [
    ["learn", "bench", "--experiment", "port_clash", "--tried", "a", "--result", "b", "--recommend", "free 16379"],
    ["learn", "bench", "--experiment", "stage_paths", "--tried", "a", "--result", "b", "--recommend", "no add -A"],
    ["learn", "bench", "--experiment", "keep_me", "--tried", "a", "--result", "b", "--recommend", "x"],
    ["graduate", "bench", "--experiment", "stage_paths", "--enforced-by", "pre-commit hook"],
]
RUNS = {
    "queue": ["memreplay", "queue"],
    "snapshot": ["memreplay", "snapshot", "--label", "bench"],
    "run": ["memreplay", "run", "--lesson", "port_clash"],
    "drain": ["memreplay", "drain", "--base", "baseline"],
}
EMPTY = ["memreplay", "queue"]
QUESTIONS = [
    {"run": "queue", "q": "How many lessons are queued for a memory replay?", "a": 3, "grade": "number"},
    {"run": "queue", "q": "Why was the lesson stage_paths queued? Give the reason only.", "a": "new", "grade": "exact"},
    {"run": "snapshot", "q": "Was a snapshot written? Answer yes or no.", "a": "yes", "grade": "exact"},
    {
        "run": "run",
        "q": "Which flag is missing from this memreplay run command? Give the flag only.",
        "a": "--base",
        "grade": "contains",
    },
    {
        "run": "drain",
        "q": "Which flag is missing from this memreplay drain command? Give the flag only.",
        "a": "--daily-usd",
        "grade": "contains",
    },
]
