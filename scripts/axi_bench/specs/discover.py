"""AXI bench spec: `discover` -- the self-describing door: every verb and its purpose.

The --semantic path makes a model call, so the bench reads only the substring search."""

VERB = "discover"
SEED: list = []  # the verb table is code, not stored data
RUNS = {
    "all": ["discover"],
    "lock": ["discover", "lock"],
    "none": ["discover", "zzzz_nothing"],
}
EMPTY = ["discover", "zzzz_nothing"]
QUESTIONS = [
    {"run": "all", "q": "How many verbs does this CLI have in total?", "a": 121, "grade": "number"},
    {"run": "all", "q": "Which verb is described as the smallest verb in the house?", "a": "boop", "grade": "exact"},
    {"run": "lock", "q": "How many verbs matched the search?", "a": 12, "grade": "number"},
    {"run": "lock", "q": "Which verb releases an advisory path-lock?", "a": "unlock", "grade": "exact"},
    {"run": "none", "q": "How many verbs matched the search?", "a": 0, "grade": "number"},
    {
        "run": "none",
        "q": "No verb matched. What is the full command to search for the capability by meaning instead? "
        "Give the command only.",
        "a": ["discover --semantic", "zzzz_nothing"],
        "grade": "contains",
    },
]
