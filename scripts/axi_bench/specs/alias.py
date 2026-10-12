"""AXI bench spec: `alias` -- author, list, retire and trace toolbelt aliases.

The toolbelt lives in the checkout (data/verb-registry/<agent>.json), not in the store, so a
SEED written with the working tree's CLI would never reach the exported "before" tree. The runs
build the state themselves instead, in order, inside whichever tree is being measured.
"""

VERB = "alias"
SEED = []
RUNS = {
    "mint": ["alias", "bench", "mint", "land", "--step", "status", "--step", "locks", "--family", "RHYTHM",
             "--why", "close the day"],
    "mint_scan": ["alias", "bench", "mint", "scan", "--step", "locks", "--evidence", "VERIFIED",
                  "--tested-against", "pin-42", "--family", "SENTINELS"],
    "mint_peek": ["alias", "bench", "mint", "peek", "--step", "status"],
    "remint": ["alias", "bench", "mint", "land", "--step", "status", "--family", "RHYTHM"],
    "retire": ["alias", "bench", "retire", "peek", "--reason", "unused"],
    "list": ["alias", "bench", "list"],
    "history": ["alias", "bench", "history", "land"],
    "missing": ["alias", "bench", "retire", "ghost"],
}  # fmt: skip
EMPTY = ["alias", "nobody", "list"]
QUESTIONS = [
    {"run": "mint", "q": "What version number did the alias get?", "a": 1, "grade": "number"},
    {
        "run": "mint",
        "q": "What exact command runs the alias that was just minted? Give the command only.",
        "a": ["run bench land"],
        "grade": "contains",
    },
    {"run": "list", "q": "How many active aliases does bench have?", "a": 2, "grade": "number"},
    {"run": "list", "q": "What evidence level does the scan alias have?", "a": "VERIFIED", "grade": "exact"},
    {"run": "list", "q": "Which version of the land alias is active?", "a": 2, "grade": "number"},
    {"run": "missing", "q": "Did retiring ghost succeed? Answer yes or no.", "a": "no", "grade": "exact"},
]
