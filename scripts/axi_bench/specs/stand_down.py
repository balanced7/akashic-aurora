"""AXI bench spec: `stand-down` -- yield this session's consumer seat for good.

Only the no-session path is benched: the bench strips every CLAUDE* variable from the CLI's
environment, so no run has a session to yield. The yield itself is pinned in tests.
"""

VERB = "stand-down"
SEED = []
RUNS = {"no_session": ["stand-down", "claude"]}
EMPTY = None
QUESTIONS = [
    {"run": "no_session", "q": "Was the seat yielded? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "no_session",
        "q": "Which environment variable must be set for this command to work? Give its name only.",
        "a": "CLAUDE_CODE_SESSION_ID",
        "grade": "exact",
    },
    {"run": "no_session", "q": "Which agent's seat was this command about?", "a": "claude", "grade": "exact"},
]
