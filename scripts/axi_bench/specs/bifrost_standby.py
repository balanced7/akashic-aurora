"""AXI bench spec: `bifrost-standby` -- drain the inbox and report the seat.

Only the non-blocking report (--no-listen) is benched: without it the verb blocks as the wake
listener's parent until mail arrives, which is the harness's job, not a reader's.
"""

VERB = "bifrost-standby"
SEED = [
    ["bifrost-send", "deepseek", "please review core/a.py", "--to", "claude", "--kind", "request"],
    ["bifrost-send", "deepseek", "fyi the build is green", "--to", "claude"],
]
RUNS = {
    "drain": ["bifrost-standby", "claude", "--no-listen"],
    "clean": ["bifrost-standby", "claude", "--no-listen"],
}
EMPTY = ["bifrost-standby", "claude", "--no-listen"]
QUESTIONS = [
    {"run": "drain", "q": "How many messages were drained?", "a": 2, "grade": "number"},
    {"run": "drain", "q": "Which agent sent the request message?", "a": "deepseek", "grade": "exact"},
    {
        "run": "drain",
        "q": "Is a wake listener now waiting for new mail for this agent? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {"run": "clean", "q": "How many messages did this run drain?", "a": 0, "grade": "number"},
    {
        "run": "drain",
        "q": "What exact command would drain the inbox and then wait for new mail? Give the command only.",
        "a": ["bifrost-standby", "claude"],
        "grade": "contains",
    },
]
