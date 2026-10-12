"""AXI bench spec: `kit` -- inspect and install the recovery-kit on a seat's toolbelt.

The toolbelt lives in the checkout (data/verb-registry/<agent>.json), so the runs build the
state themselves, in order, inside whichever tree is being measured: one alias minted first so
the install supersedes it, the install, then the same install again (nothing changes). Two of
the kit's four entries name verbs the CLI no longer has, so the install really refuses them.
"""

VERB = "kit"
SEED = []
RUNS = {
    "show": ["kit", "bench", "--show"],
    "premint": ["alias", "bench", "mint", "standby-hard", "--step", "doctor"],
    "install": ["kit", "bench"],
    "again": ["kit", "bench"],
    "unknown": ["kit", "bench", "nope-kit"],
}
EMPTY = None
QUESTIONS = [
    {"run": "show", "q": "How many entries does the recovery-kit have?", "a": 4, "grade": "number"},
    {"run": "show", "q": "What evidence level does the drain-decide entry carry?", "a": "VERIFIED", "grade": "exact"},
    {"run": "install", "q": "Which entry replaced an alias that already existed? Give its name only.",
     "a": "standby-hard", "grade": "exact"},
    {"run": "install", "q": "Which entries were refused? List them separated by commas.",
     "a": ["vitals", "premise-check"], "grade": "set"},
    {"run": "again", "q": "Did the second install change any entry? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "unknown", "q": "Which kits are available? Give the names only.", "a": ["recovery-kit"],
     "grade": "contains"},
]  # fmt: skip
