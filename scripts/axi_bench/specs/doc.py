"""AXI bench spec: `doc` -- the library's birth door, error paths only.

A successful `doc new`, `doc adopt` or `doc arc` writes into the checkout itself: it appends to
the tracked store/docs/<type>.jsonl and renders docs/library/<type>/<file>.md beside the code,
and the bench's "after" side runs from the working tree. So only what refuses before writing is
benched: the bare verb, a missing or unknown type, an unknown atom and a missing file.
"""

VERB = "doc"
SEED = []
RUNS = {
    "bare": ["doc"],
    "notype": ["doc", "new", "--title", "probe-x"],
    "badtype": ["doc", "new", "--type", "bogus", "--title", "probe-x", "--body", "y"],
    "noatom": ["doc", "arc", "art_20990101_nope_000000", "newlabel"],
    "nofile": ["doc", "adopt", "/nonexistent/axi-bench-nope.md"],
}
EMPTY = None
QUESTIONS = [
    {
        "run": "bare",
        "q": "Which subcommands does the doc command offer? List them separated by commas.",
        "a": ["new", "adopt", "arc"],
        "grade": "set",
    },
    {"run": "notype", "q": "Did the command succeed? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "notype",
        "q": "Which atom types does doc new accept? List them separated by commas.",
        "a": ["contract", "map", "design", "brief", "report", "chronicle", "ledger", "ruling"],
        "grade": "set",
    },
    {
        "run": "badtype",
        "q": "Which type did the command reject? Give the type only.",
        "a": "bogus",
        "grade": "exact",
    },
    {
        "run": "noatom",
        "q": "Which atom id could not be found? Give the id only.",
        "a": "art_20990101_nope_000000",
        "grade": "exact",
    },
    {"run": "nofile", "q": "Did the adopt succeed? Answer yes or no.", "a": "no", "grade": "exact"},
]
