"""AXI bench spec: `focus` -- which task this session's tool calls are attributed to.

The task comes from the sandbox ledger (the harness points AKASHIC_TASKS_PATH into the sandbox),
and every run names its session, because the bench strips the harness session id."""

VERB = "focus"
SEED = [
    ["task", "propose", "Fix the login redirect", "--files", "core/auth.py,core/session.py", "--by", "bench"],
    ["focus", "bench", "--session", "s1", "--set", "T001"],
]
RUNS = {
    "show": ["focus", "bench", "--session", "s1"],
    "none": ["focus", "bench", "--session", "s2"],
    "set": ["focus", "bench", "--session", "s3", "--set", "T001"],
}
EMPTY = ["focus", "bench", "--session", "s9"]
QUESTIONS = [
    {"run": "show", "q": "Which task is this session focused on?", "a": "T001", "grade": "exact"},
    {"run": "show", "q": "How many tool calls have been attributed to the focused task?", "a": 0, "grade": "number"},
    {"run": "none", "q": "Does this session have a focus? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "set",
        "q": "Which files does the drift check watch for this task? List them separated by commas.",
        "a": ["core/auth.py", "core/session.py"],
        "grade": "set",
    },
    {"run": "set", "q": "What is the ledger status of the focused task?", "a": "proposed", "grade": "exact"},
    {
        "run": "show",
        "q": "What exact command checks this session out of its focus? Give the command only.",
        "a": ["focus", "--clear"],
        "grade": "contains",
    },
]
