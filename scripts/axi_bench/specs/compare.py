"""AXI bench spec: `compare` -- the set difference between two like domains.

Only the store-backed domain (lessons:all) and the offline paths are measured: the code
domains (verbs, files, terms) read the checkout itself, and the two sides of the bench are
different checkouts, so their keys would differ for reasons that have nothing to do with the
output format.
"""

VERB = "compare"
SEED = [
    ["learn", "bench", "--experiment", "port_clash", "--tried", "a", "--result", "b"],
    ["learn", "bench", "--experiment", "git_staging", "--tried", "a", "--result", "b"],
    ["learn", "alice", "--experiment", "token_refresh", "--tried", "a", "--result", "b"],
]
RUNS = {
    "list": ["compare", "--list"],
    "same": ["compare", "lessons:all", "lessons:all"],
    "refused": ["compare", "verbs:cli", "files:tracked"],
}
EMPTY = ["compare", "lessons:all", "lessons:all"]
QUESTIONS = [
    {"run": "list", "q": "What kind of key does the files:tracked domain use?", "a": "path", "grade": "exact"},
    {"run": "list", "q": "How many comparable domains are listed?", "a": 7, "grade": "number"},
    {"run": "same", "q": "How many keys are in both sides?", "a": 3, "grade": "number"},
    {"run": "same", "q": "Is this comparison result reliable? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "refused", "q": "Was the comparison carried out? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "refused",
        "q": "What kind of key does the verbs:cli domain use?",
        "a": "verb",
        "grade": "exact",
    },
]
