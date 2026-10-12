"""AXI bench spec: `review` -- the human review queue, on its offline paths.

`review apply` and `review rollback` write into the live checkout, so they never run here.
The seed queues two candidates with `review add` (a verdict over no graded runs, an HTML page
in the sandbox); the runs read the queue, the watch list, the disagreements and a missing item."""

VERB = "review"
SEED = [
    ["replay", "new", "--candidate", "opus-high", "--harness", "claude-code", "--effort", "high"],
    ["replay", "new", "--candidate", "codex-low", "--harness", "codex-cli", "--effort", "low"],
    ["review", "add", "--candidate", "opus-high", "--against", "baseline", "--scenario", "T1-abc"],
    ["review", "add", "--candidate", "codex-low", "--against", "baseline", "--scenario", "T1-abc"],
]
RUNS = {
    "list": ["review", "list"],
    "watch": ["review", "watch"],
    "disagreements": ["review", "disagreements"],
    "missing": ["review", "show", "nope-123456"],
}
EMPTY = ["review", "list"]
QUESTIONS = [
    {"run": "list", "q": "How many items are waiting for review?", "a": 2, "grade": "number"},
    {
        "run": "list",
        "q": "How many reviewers must accept the codex-low item before it is accepted?",
        "a": 1,
        "grade": "number",
    },
    {
        "run": "list",
        "q": "Which candidate is the opus-high item compared against?",
        "a": "baseline",
        "grade": "exact",
    },
    {"run": "watch", "q": "How many applied changes are under watch?", "a": 0, "grade": "number"},
    {
        "run": "disagreements",
        "q": "How many person/grader disagreements are recorded?",
        "a": 0,
        "grade": "number",
    },
    {"run": "missing", "q": "Does the review item nope-123456 exist? Answer yes or no.", "a": "no", "grade": "exact"},
]
