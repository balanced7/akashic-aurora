"""AXI bench spec: `run` -- execute a toolbelt alias, step by step.

The toolbelt lives in the checkout (data/verb-registry/<agent>.json), so the runs mint the
aliases themselves, in order, inside whichever tree is being measured. Steps are read-only verbs
(alias list, locks) and one that fails on purpose (discharging a defer item that does not exist,
which refuses before it writes anything).
"""

VERB = "run"
SEED = []
RUNS = {
    "mint_ok": ["alias", "bench", "mint", "check", "--step", "alias bench list", "--step", "locks"],
    "mint_bad": ["alias", "bench", "mint", "broken", "--step", "locks", "--step",
                 "defer bench --done nope --receipt x", "--step", "alias bench list"],
    "mint_macro": ["alias", "bench", "mint", "hist", "--step", "alias bench history $1"],
    "ok": ["run", "bench", "check"],
    "bad": ["run", "bench", "broken"],
    "dry": ["run", "bench", "hist", "land", "--dry"],
    "missing": ["run", "bench", "ghost"],
}  # fmt: skip
EMPTY = None
QUESTIONS = [
    {"run": "ok", "q": "Did every step of the alias finish successfully? Answer yes or no.", "a": "yes",
     "grade": "exact"},
    {"run": "bad", "q": "Which step number failed?", "a": 2, "grade": "number"},
    {"run": "bad", "q": "What exit code did the failing step return?", "a": 2, "grade": "number"},
    {"run": "bad", "q": "Was the step `alias bench list` run? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "dry", "q": "What exact command would the first step run? Give the command only.",
     "a": ["alias bench history land"], "grade": "contains"},
    {"run": "missing", "q": "Which aliases does bench have? List them separated by commas.",
     "a": ["broken", "check", "hist"], "grade": "set"},
]  # fmt: skip
