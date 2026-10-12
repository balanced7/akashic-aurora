"""AXI bench spec: `audit` -- MATCH/DRIFT/UNKNOWN rows over durable beliefs vs ground truth.

The audit reads the repo itself (data/verb-registry, the live parser, the lexicon table), not the
store, so there is nothing to seed and no empty store to show: the answers below are the repo's
own rows, identical in the before and after trees.
"""

VERB = "audit"
SEED: list = []
RUNS = {"all": ["audit"], "bad": ["audit", "--domain", "nope"]}
EMPTY = None
QUESTIONS = [
    {"run": "all", "q": "How many rows have the verdict DRIFT in total?", "a": 17, "grade": "number"},
    {"run": "all", "q": "What verdict does the entry deepseek:parse-gate have?", "a": "MATCH", "grade": "exact"},
    {"run": "all", "q": "Which rule fired for the entry deepseek:vitals?", "a": "sugar-only", "grade": "exact"},
    {"run": "all", "q": "How many rows did the stale-receipt rule fire on?", "a": 14, "grade": "number"},
    {"run": "all", "q": "What verdict does the SPEND domain's only row have?", "a": "UNKNOWN", "grade": "exact"},
    {
        "run": "bad",
        "q": "Which domain names can be audited? List them separated by commas.",
        "a": ["VERBS", "SPEND", "LEXICON"],
        "grade": "set",
    },
]
