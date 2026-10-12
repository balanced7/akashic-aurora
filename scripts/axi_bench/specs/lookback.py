"""AXI bench spec: `lookback` -- one why-question over the rationale corpus.

Only the notes layer is asked (--layers notes): the docs, research and git layers read the
checkout, and the two sides of the bench are different checkouts (the baseline export has no
.git), so their hits would differ for reasons unrelated to the output format.
"""

VERB = "lookback"
SEED = [
    ["note", "alice", "--title", "Chose quokkadb for the embedded store",
     "--note", "We picked quokkadb over leveldb because it ships with python and survives crashes"],
    ["note", "bob", "--title", "Redis port moved to 16379",
     "--note", "The embedded redis listens on 16379 so it never clashes with a system redis on 6379"],
    ["note", "bob", "--title", "Old cache design",
     "--note", "The quokkadb cache layer was dropped in favour of redis"],
    ["note", "bob", "--retire", "Old cache design"],
]  # fmt: skip
RUNS = {
    "why": ["lookback", "why", "quokkadb", "--layers", "notes"],
    "none": ["lookback", "zebra", "unicorn", "--layers", "notes"],
}
EMPTY = ["lookback", "anything", "--layers", "notes"]
QUESTIONS = [
    {"run": "why", "q": "How many hits did the lookback return?", "a": 2, "grade": "number"},
    {
        "run": "why",
        "q": "Is the hit about the old cache design current or retired? Answer current or retired.",
        "a": "retired",
        "grade": "exact",
    },
    {
        "run": "why",
        "q": "According to the top hit, what was quokkadb picked over?",
        "a": "leveldb",
        "grade": "exact",
    },
    {"run": "why", "q": "Which corpus layer did the hits come from?", "a": "notes", "grade": "exact"},
    {"run": "none", "q": "How many hits did the lookback return?", "a": 0, "grade": "number"},
]
