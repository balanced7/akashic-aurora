"""AXI bench spec: `ask` -- offline paths only.

Every real ask calls a paid model, so the bench never reaches one: it reads the empty background
register (--list), an unknown handle (--get) and an unknown durable ask (--status), and runs the
refusals that fire before any model call (--bg with --get, and --as-resident for a seat that is
not a resident). The answer shape itself is pinned by tests/test_axi_ask.py with a fake helper.
"""

VERB = "ask"
SEED = []
RUNS = {
    "list": ["ask", "--list"],
    "get": ["ask", "--get", "deadbeef"],
    "status": ["ask", "--status", "42"],
    "conflict": ["ask", "--bg", "--get", "x"],
    "resident": ["ask", "--as-resident", "nobody", "what is two plus two"],
}
EMPTY = ["ask", "--list"]
QUESTIONS = [
    {"run": "list", "q": "How many background asks are recorded?", "a": 0, "grade": "number"},
    {"run": "get", "q": "Does an ask with handle deadbeef exist? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "get",
        "q": "What exact command lists the recent background asks? Give the command only.",
        "a": ["ask --list"],
        "grade": "contains",
    },
    {"run": "status", "q": "Is ask 42 in a terminal state? Answer yes or no.", "a": "yes", "grade": "exact"},
    {
        "run": "conflict",
        "q": "Which flag should be run first, --bg or --get? Answer with the flag only.",
        "a": "--bg",
        "grade": "exact",
    },
    {"run": "resident", "q": "Did the ask succeed? Answer yes or no.", "a": "no", "grade": "exact"},
]
