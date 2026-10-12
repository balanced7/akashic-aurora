"""AXI bench spec: `recall-counters` -- fold bare-slug and ghost recall counters.

Votes are canonicalized when cast, and impressions are counted only by the harness hooks, so the
CLI can seed neither a bare slug nor a zero-credit ghost. What it can seed is credited ghosts:
votes on lessons that do not exist, which the fold keeps for a human decision.
"""

VERB = "recall-counters"
SEED = [
    ["learn", "alice", "--experiment", "alive_one", "--tried", "a", "--result", "b", "--recommend", "Use when x: y."],
    ["recall-feedback", "--source", "learn:experiment:renamed_away", "--useful"],
    ["recall-feedback", "--source", "learn:experiment:retired_rule", "--noise"],
]
RUNS = {"report": ["recall-counters"], "fold": ["recall-counters", "--fold"]}
EMPTY = ["recall-counters"]
QUESTIONS = [
    {"run": "report", "q": "How many bare-slug counters would be merged?", "a": 0, "grade": "number"},
    {"run": "report", "q": "How many credited ghost counters are kept?", "a": 2, "grade": "number"},
    {
        "run": "report",
        "q": "Which credited ghosts are kept? List their sources separated by commas.",
        "a": ["learn:experiment:renamed_away", "learn:experiment:retired_rule"],
        "grade": "set",
    },
    {"run": "report", "q": "Did this run change anything? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "fold", "q": "How many zero-credit ghosts were pruned?", "a": 0, "grade": "number"},
    {
        "run": "report",
        "q": "What exact command applies the fix? Give the command only.",
        "a": ["recall-counters", "--fold"],
        "grade": "contains",
    },
]
