"""AXI bench spec: `wish` -- file an ergonomics wish, against a throwaway ledger.

The ledger is docs/WISHLIST.md unless AKASHIC_WISHLIST_FILE says otherwise, so this module
writes a small ledger to a temporary file when it is loaded and points the variable at it; every
run inherits it and the tracked docs/WISHLIST.md is never touched. The ledger sits outside the
sandbox reset, so each side's filing appends one more wish: the questions never ask for the new
id, which differs by one between the sides. The ledger carries a collided id (W02 twice) on
purpose, so the collision warning shows.
"""

import os
import tempfile
from pathlib import Path

LEDGER = """# WISHLIST -- bench double

## Open

- [ ] W01 (07-18, claude) — Make recall faster on big stores.
- [ ] W02 (07-20, kimi) — Show lock ttl in human units.
- [ ] W02 (07-21, sol) — A duplicate id from a stale read.
- [ ] W03 (08-01, deepseek) — Doctor should name the dead seat.

## Folded

- [x] W00 (07-01, claude) — The first wish.

## Declined

*(none yet — when one lands here, it keeps its reason.)*
"""

_path = Path(tempfile.mkdtemp(prefix="axi-wish-")) / "WISHLIST.md"
_path.write_text(LEDGER, encoding="utf-8")
os.environ["AKASHIC_WISHLIST_FILE"] = str(_path)

VERB = "wish"
SEED = []
RUNS = {
    "file": ["wish", "bench", "Make", "the", "status", "verb", "faster", "--trigger", "status took 9s"],
    "empty": ["wish", "bench"],
}
EMPTY = None  # the verb files; it has no listing to be empty
QUESTIONS = [
    {"run": "file", "q": "Was the wish filed? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "file", "q": "Which agent is the new wish attributed to?", "a": "bench", "grade": "exact"},
    {
        "run": "file",
        "q": "Which wish id appears more than once in the ledger? Give the id only.",
        "a": "W02",
        "grade": "exact",
    },
    {"run": "empty", "q": "Was a wish filed? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "empty",
        "q": "What does the command need that was missing? Answer in a few words.",
        "a": ["text"],
        "grade": "contains",
    },
]
