"""AXI bench spec: `recall` -- search past lessons."""

LONG = (
    "Use when a token refresh fails with 401 after an idle period, before retrying the request: "
    "refresh the token once, then retry. "
    + "The refresh window is 300 seconds and a second failure means the session is revoked. "
    * 6
)

VERB = "recall"
SEED = [
    ["learn", "bench", "--experiment", "port_clash", "--tried", "ran the suite", "--result", "hung at start",
     "--recommend", "Use when tests hang at start: check that port 16379 is free first.", "--category",
     "performance", "--success", "yes"],
    ["learn", "bench", "--experiment", "git_blanket_staging", "--tried", "git add -A", "--result", "staged a secret",
     "--recommend", "Stage explicit paths, never git add -A.", "--category", "correction", "--success", "no"],
    ["learn", "alice", "--experiment", "auth_token_refresh", "--tried", "retried blindly", "--result", "locked out",
     "--recommend", LONG, "--category", "security", "--success", "partial"],
    ["graduate", "bench", "--experiment", "git_blanket_staging", "--enforced-by", "pre-commit hook"],
]  # fmt: skip
RUNS = {
    "port": ["recall", "port"],
    "git": ["recall", "git"],
    "auth": ["recall", "token"],
    "none": ["recall", "nonexistent_xyz"],
}
EMPTY = ["recall", "anything"]
QUESTIONS = [
    {"run": "port", "q": "Which port should be checked when tests hang at start?", "a": 16379, "grade": "number"},
    {"run": "port", "q": "Which category is the port_clash lesson in?", "a": "performance", "grade": "exact"},
    {
        "run": "git",
        "q": "Is the git_blanket_staging lesson active, or has it been graduated? Answer active or graduated.",
        "a": "graduated",
        "grade": "exact",
    },
    {"run": "none", "q": "How many lessons matched the search?", "a": 0, "grade": "number"},
    {
        "run": "auth",
        "q": "What exact command would show the complete record of the auth_token_refresh lesson? "
        "Give the command only.",
        "a": ["--full", "learn:experiment:auth_token_refresh"],
        "grade": "contains",
    },
]
