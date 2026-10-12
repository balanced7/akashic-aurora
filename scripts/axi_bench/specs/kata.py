"""AXI bench spec: `kata` -- check an alias's steps against the CLI's own grammar.

The toolbelt lives in the checkout (data/verb-registry/<agent>.json), so the runs mint the
aliases themselves, in order, inside whichever tree is being measured. Minting only checks each
step's verb; the unknown flag in `bad` is what kata is for.
"""

VERB = "kata"
SEED = []
RUNS = {
    "mint_good": ["alias", "bench", "mint", "good", "--step", "locks", "--step", "alias bench list"],
    "mint_bad": ["alias", "bench", "mint", "bad", "--step", "locks", "--step", "alias bench list --nope"],
    "mint_done": ["alias", "bench", "mint", "done", "--step", "locks", "--evidence", "VERIFIED",
                  "--tested-against", "pin-1"],
    "good": ["kata", "bench", "good"],
    "bad": ["kata", "bench", "bad"],
    "done": ["kata", "bench", "done"],
    "missing": ["kata", "bench", "ghost"],
}  # fmt: skip
EMPTY = None
QUESTIONS = [
    {"run": "good", "q": "What evidence level does the alias have now?", "a": "VERIFIED", "grade": "exact"},
    {"run": "good", "q": "What version number is the alias now?", "a": 2, "grade": "number"},
    {"run": "bad", "q": "Which step failed the grammar check? Give the step's command only.",
     "a": ["--nope"], "grade": "contains"},
    {"run": "bad", "q": "What evidence level does the alias have after this check?", "a": "GUESS",
     "grade": "exact"},
    {"run": "done", "q": "Did this check change the alias's evidence level? Answer yes or no.", "a": "no",
     "grade": "exact"},
    {"run": "missing", "q": "Does bench have an alias called ghost? Answer yes or no.", "a": "no",
     "grade": "exact"},
]  # fmt: skip
