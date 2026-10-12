"""AXI bench spec: `forecast` -- the engineering forecast registry.

READ PATHS ONLY. The registry is a file inside the repo (state/coord/forecasts.jsonl, committed),
and `register` / `score` append to it with no way to point them elsewhere, so the bench never
writes: it reads the committed registry (identical in both trees) with `list` and
`list --calibration`, and checks the usage error a bare `register` gives before it writes
anything. The overdue list depends on today's date, the same for both sides of one run.
"""

# Two words: the conformance checks append a bogus flag to the verb and its required action;
# without the action argparse reports it missing before it sees the flag.
VERB = "forecast list"
SEED: list = []
RUNS = {
    "list": ["forecast", "list"],
    "calibration": ["forecast", "list", "--calibration"],
    "no_id": ["forecast", "register"],
    "refused": ["forecast", "score", "F999", "--verdict", "hit"],  # refused before any write
}
EMPTY = None
QUESTIONS = [
    {"run": "list", "q": "How many forecasts are registered in total?", "a": 15, "grade": "number"},
    {"run": "list", "q": "What verdict does forecast F008 have?", "a": "partial", "grade": "exact"},
    {"run": "list", "q": "How many forecasts are still open (not yet scored)?", "a": 5, "grade": "number"},
    {"run": "list", "q": "Which seat registered forecast F004?", "a": "deepseek", "grade": "exact"},
    {"run": "calibration", "q": "What is claude's hit rate, as a percentage?", "a": 50, "grade": "number"},
    {
        "run": "calibration",
        "q": "Which forecasts are overdue? List their ids separated by commas.",
        "a": ["F004", "F005", "F012", "F013"],
        "grade": "set",
    },
    {
        "run": "no_id",
        "q": "Which flag does `forecast register` need that was not given? Give the flag only.",
        "a": "--id",
        "grade": "contains",
    },
    {
        "run": "refused",
        "q": "Was the score recorded? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
]
