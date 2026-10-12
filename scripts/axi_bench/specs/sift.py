"""AXI bench spec: `sift` -- the dry run and a refusal, offline.

A real sift fans its hats to a paid model, so the bench runs only --dry-run (tier 0: evidence
packs built from the repo's own source, nothing spent) and an unknown hat, which is refused
before any evidence is gathered. The terms were chosen for counts that are identical in the
baseline tree and this one (22 source occurrences in 9 files, and none). This spec is itself a
source file of the tree under test, so the terms are spelled in two halves here: writing them
whole would add this file to their own evidence and move the counts.
"""

TERM = "wake" + "able"
ABSENT = "cursor" + "_lease"

VERB = "sift"
SEED = []
RUNS = {
    "dry": ["sift", TERM, ABSENT, "--dry-run"],
    "badhat": ["sift", TERM, "--hats", "nosuchhat", "--dry-run"],
}
EMPTY = None
QUESTIONS = [
    {"run": "dry", "q": f"How many occurrences of '{TERM}' are in its evidence pack?", "a": 22, "grade": "number"},
    {"run": "dry", "q": f"In how many files does '{TERM}' occur?", "a": 9, "grade": "number"},
    {"run": "dry", "q": f"How many occurrences of '{ABSENT}' were found?", "a": 0, "grade": "number"},
    {
        "run": "dry",
        "q": "Was any money spent on model calls by this command? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "badhat",
        "q": "Which hats does sift accept? List them separated by commas.",
        "a": ["adversary", "historian", "jester", "junction", "linguist", "outsider"],
        "grade": "set",
    },
    {"run": "badhat", "q": "Did the command succeed? Answer yes or no.", "a": "no", "grade": "exact"},
]
