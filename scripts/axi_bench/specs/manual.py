"""AXI bench spec: `manual` -- the manuals shelf (list, search).

The shelf lives under the sandbox (AI_SETUP/state/manuals), so it starts empty: EMPTY measures
the empty shelf as it is. The seeded runs shelve docs/library/contract (three runbooks, read
from the checkout by the working tree's CLI, so both sides search the same passages). Search
uses --mode bm25: there is no embedding model on the bench machine, and hybrid would fall back
to keywords anyway, with a note.
"""

VERB = "manual"
SEED = [["manual", "ingest", "runbooks", "docs/library/contract"]]
RUNS = {
    "list": ["manual", "list"],
    "search": ["manual", "search", "how", "do", "I", "recover", "a", "wedged", "seat", "--mode", "bm25", "--limit",
               "2"],
    "none": ["manual", "search", "zebra", "unicorn", "--mode", "bm25"],
}  # fmt: skip
EMPTY = ["manual", "list"]
QUESTIONS = [
    {"run": "list", "q": "How many passages are on the shelf in total?", "a": 20, "grade": "number"},
    {"run": "list", "q": "What is the name of the shelf?", "a": "runbooks", "grade": "exact"},
    {
        "run": "search",
        # The runbook's file name and its own first heading ("THE UNWEDGE RUNBOOK") are both
        # fair answers to "title", so either is accepted.
        "q": "Which document did the top passage come from? Give its title.",
        "a": "unwedge",
        "grade": "contains",
    },
    {
        "run": "search",
        "q": "Was the answer cut short by the size or count cap? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
    {"run": "none", "q": "How many passages matched the question?", "a": 0, "grade": "number"},
]
