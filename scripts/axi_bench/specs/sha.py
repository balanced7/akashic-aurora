"""AXI bench spec: `sha` -- resolve a pre-rewrite commit SHA through the rewrite maps.

Offline only: --no-remote skips the clone-visibility probe (the exported before-tree has no
.git to probe), and the maps are the tree's own state/rewrites, identical on both sides."""

VERB = "sha"
SEED: list = []
RUNS = {
    "maps": ["sha", "--maps"],
    "resolve": ["sha", "00cf320d", "01051640", "deadbeef1", "--no-remote"],
    "bad": ["sha", "zzzz", "--no-remote"],
}
EMPTY = None  # no store behind it: the maps are files in the tree
QUESTIONS = [
    {"run": "maps", "q": "How many rewrite maps does this checkout carry?", "a": 5, "grade": "number"},
    {"run": "maps", "q": "How many remaps does the 2026-08-12 map hold?", "a": 1979, "grade": "number"},
    {
        "run": "resolve",
        "q": "Which commit does 00cf320d finally resolve to? Give its SHA.",
        "a": ["fdccf166e157"],
        "grade": "contains",
    },
    {"run": "resolve", "q": "How many of the cited SHAs could not be resolved?", "a": 1, "grade": "number"},
    {
        "run": "resolve",
        # (Asking which maps a SHA passed through drew UNKNOWN from the reader on both sides,
        # whatever the wording or the column name, so the spec asks what it can grade.)
        "q": "Why could deadbeef1 not be resolved? Answer in a few words.",
        "a": ["no map"],
        "grade": "contains",
    },
    {"run": "bad", "q": "Is zzzz a valid commit SHA? Answer yes or no.", "a": "no", "grade": "exact"},
]
