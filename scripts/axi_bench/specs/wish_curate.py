"""AXI bench spec: `wish-curate` -- the wishlist's disposition door, read path and refusals.

Runs against a throwaway ledger (AKASHIC_WISHLIST_FILE, written when this module loads); the
tracked docs/WISHLIST.md is never touched. Only what does not write is benched: the listing of
the oldest open wishes and two refusals (an unknown id, a decline without a reason). A real
disposition rewrites the ledger and is pinned in tests instead.
"""

import os
import tempfile
from pathlib import Path

LEDGER = """# WISHLIST -- bench double

## Open

- [ ] W01 (07-18, claude) — Make recall faster on big stores.
- [ ] W02 (07-20, kimi) — Show lock ttl in human units.
- [ ] W03 (08-01, deepseek) — Doctor should name the dead seat.
- [ ] W05 (08-03, sol) — Let boot take a smaller token budget.
- [ ] W06 (08-09, claude) — Wake should say which seat woke it.

## Folded

- [x] W00 (07-01, claude) — The first wish.
  FOLDED 07-02 (claude) -> T001.
- [x] W04 (07-25, kimi) — Recall should print sources.
  FOLDED 08-01 (claude) -> T120.

## Declined

*(none yet — when one lands here, it keeps its reason.)*
"""

_path = Path(tempfile.mkdtemp(prefix="axi-wish-curate-")) / "WISHLIST.md"
_path.write_text(LEDGER, encoding="utf-8")
os.environ["AKASHIC_WISHLIST_FILE"] = str(_path)

VERB = "wish-curate"
SEED = []
RUNS = {
    "list": ["wish-curate", "bench"],
    "unknown": ["wish-curate", "bench", "--id", "W77", "--as", "keep", "--reason", "still wanted"],
    "noreason": ["wish-curate", "bench", "--id", "W01", "--as", "decline"],
}
EMPTY = None  # the ledger is outside the sandbox reset
QUESTIONS = [
    {"run": "list", "q": "How many wishes are open?", "a": 5, "grade": "number"},
    {"run": "list", "q": "How many wishes have been folded?", "a": 2, "grade": "number"},
    {"run": "list", "q": "Which is the oldest open wish? Give its id only.", "a": "W01", "grade": "exact"},
    {"run": "list", "q": "Who filed wish W03?", "a": "deepseek", "grade": "exact"},
    {
        "run": "list",
        "q": "What command declines wish W02? Give the command only.",
        "a": ["wish-curate bench", "--id w02", "--as decline", "--reason"],
        "grade": "contains",
    },
    {"run": "noreason", "q": "Was the wish declined? Answer yes or no.", "a": "no", "grade": "exact"},
]
