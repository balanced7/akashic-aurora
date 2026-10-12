"""AXI bench spec: `recall-curate` -- bench lessons that never earn credit, prune ghost counters.

Offline paths only: the report, --apply, the Forge audit, the proposal queue and the --forge-check
usage error. --forge-propose calls a model and is not benched. Impressions are counted by the
harness hooks, which no CLI verb can drive, so nothing here is surfaced often enough to bench;
the ghost is a counter voted on a lesson that does not exist.
"""

VERB = "recall-curate"
SEED = [
    ["learn", "alice", "--experiment", "keep_one", "--tried", "a", "--result", "b", "--recommend", "Use when x: y."],
    ["learn", "alice", "--experiment", "keep_two", "--tried", "a", "--result", "b", "--recommend", "Use when z: w."],
    ["learn", "alice", "--experiment", "hooked", "--tried", "a", "--result", "b", "--recommend", "Use when q: r."],
    ["graduate", "alice", "--experiment", "hooked", "--enforced-by", "pre-commit hook"],
    ["recall-feedback", "--source", "learn:experiment:renamed_away", "--useful"],
]
RUNS = {
    "report": ["recall-curate"],
    "apply": ["recall-curate", "--apply"],
    "proposals": ["recall-curate", "--forge-proposals"],
    "check": ["recall-curate", "--forge-check", "keep_one"],
    "audit": ["recall-curate", "--forge-audit"],
}
EMPTY = ["recall-curate"]
QUESTIONS = [
    {"run": "report", "q": "How many lessons are in the corpus?", "a": 3, "grade": "number"},
    {"run": "report", "q": "How many lessons are still competing for recall surface slots?", "a": 2, "grade": "number"},
    {"run": "report", "q": "How many lessons would be benched?", "a": 0, "grade": "number"},
    {"run": "report", "q": "How many credited ghost counters are kept for a decision?", "a": 1, "grade": "number"},
    {"run": "audit", "q": "What is the verdict for the c5 no-go criterion?", "a": "clear", "grade": "exact"},
    {"run": "proposals", "q": "How many optimizer proposals are pending?", "a": 0, "grade": "number"},
    {
        "run": "check",
        "q": "What does the command need that was not given? Name the flag.",
        "a": ["--draft"],
        "grade": "contains",
    },
]
