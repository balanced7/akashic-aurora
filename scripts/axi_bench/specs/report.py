"""AXI bench spec: `report` -- the scaffold written to a file, the crib, and a missing title.

The scaffold goes to a throwaway directory made when the spec loads, never into the tree under
test (the bench runs each side with its tree as the working directory). Printing the scaffold to
stdout (no --out) is the deliverable itself, unchanged, and is not benched.
"""

import tempfile
from pathlib import Path

OUT = str(Path(tempfile.mkdtemp(prefix="axi-bench-report-")) / "retro.html")

VERB = "report"
SEED = []
RUNS = {
    "write": ["report", "--title", "Q3 retro", "--out", OUT],
    "crib": ["report", "--crib"],
    "notitle": ["report"],
}
EMPTY = None
QUESTIONS = [
    {"run": "write", "q": "Which file path did the command write to? Give the path only.", "a": OUT, "grade": "exact"},
    {"run": "write", "q": "How many characters did the command write to the file?", "a": 13384, "grade": "number"},
    {"run": "crib", "q": "How many report-kit primitives are listed?", "a": 11, "grade": "number"},
    {
        "run": "crib",
        "q": "Which primitive should be used for 3-6 headline numbers? Give the primitive exactly as listed.",
        "a": ".tiles > .tile > .v + .k",
        "grade": "exact",
    },
    {
        "run": "notitle",
        "q": "Which flag is required but missing? Give the flag only.",
        "a": "--title",
        "grade": "exact",
    },
]
