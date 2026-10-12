"""AXI bench spec: `harnesses` -- the integration-tier matrix (agent/harness/registry.py).

The matrix is code, not store data, so there is nothing to seed and no empty state: the answers
are the registry's own, identical in the before and after trees.
"""

VERB = "harnesses"
SEED: list = []
RUNS = {"matrix": ["harnesses"]}
EMPTY = None
QUESTIONS = [
    {"run": "matrix", "q": "How many tiers does the cursor harness automate?", "a": 6, "grade": "number"},
    {"run": "matrix", "q": "Which agent id does the deepseek-harness use?", "a": "dsh_agent", "grade": "exact"},
    {
        "run": "matrix",
        "q": "Which harnesses automate tier T5? List them separated by commas.",
        "a": ["claude-code"],
        "grade": "set",
    },
    {
        "run": "matrix",
        "q": "In one word or hyphenated phrase, what is the cursor harness's status for tier T3?",
        "a": "one-beat-late",
        "grade": "contains",
    },
    {"run": "matrix", "q": "How many harnesses are listed?", "a": 5, "grade": "number"},
]
