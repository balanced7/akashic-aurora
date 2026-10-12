"""AXI bench spec: `injections` -- what recall pushed into agent contexts, and what it cost.

Only the harness hooks write the injection ledger, so no CLI verb can seed it: the bench measures
the empty ledger, which is what most windows of a fresh install look like. The populated view is
pinned in tests/test_axi_injections.py.
"""

VERB = "injections"
SEED = [
    ["learn", "alice", "--experiment", "conductor_stance", "--tried", "a", "--result", "b",
     "--recommend", "Use when planning: state the intent first."],
]  # fmt: skip
RUNS = {"day": ["injections"], "two_hours": ["injections", "--hours", "2"]}
EMPTY = ["injections"]
QUESTIONS = [
    {"run": "day", "q": "How many injections were there in the window?", "a": 0, "grade": "number"},
    {"run": "day", "q": "About how many tokens did recall push?", "a": 0, "grade": "number"},
    {"run": "two_hours", "q": "How many hours does the window cover?", "a": 2, "grade": "number"},
    {
        "run": "day",
        "q": "How many injections carried a lesson of the conductor family?",
        "a": 0,
        "grade": "number",
    },
]
