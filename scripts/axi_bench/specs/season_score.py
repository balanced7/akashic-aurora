"""AXI bench spec: `season-score` -- score a Season 1 round, or compare the two rule sets.

The verb reads a round file, not the store, so the fixture is written here, at import, into a
temporary directory outside the repo: six claims from three players (a first find and its
duplicate, a refuted claim, a low-confidence miss, and a claim with no evidence) and one
verification.
"""

import json
import tempfile
from pathlib import Path

_DIR = Path(tempfile.mkdtemp(prefix="axi-season-"))
ROUND = _DIR / "round.json"
_EV = ["core/comm/bus.py:120"]
ROUND.write_text(
    json.dumps(
        {
            "claims": [
                {"player": "alice", "dedupe_key": "k1", "claim_class": "structural", "outcome": "confirmed",
                 "stream_id": "1785850000001-0", "evidence": _EV},
                {"player": "bob", "dedupe_key": "k1", "claim_class": "structural", "outcome": "confirmed",
                 "stream_id": "1785850900000-0", "evidence": _EV},
                {"player": "bob", "dedupe_key": "k2", "claim_class": "needs-door", "outcome": "confirmed",
                 "stream_id": "1785850000003-0", "evidence": _EV},
                {"player": "carol", "dedupe_key": "k3", "claim_class": "dead", "outcome": "refuted",
                 "stream_id": "1785850000004-0", "evidence": _EV},
                {"player": "carol", "dedupe_key": "k4", "claim_class": "needs-door", "outcome": "confirmed",
                 "stream_id": "1785850000005-0", "evidence": []},
                {"player": "alice", "dedupe_key": "k5", "claim_class": "needs-caller", "outcome": "refuted",
                 "confidence": "low", "stream_id": "1785850000006-0", "evidence": _EV},
            ],
            "verifications": [{"player": "carol", "verdict": "confirmed"}],
        }
    ),
    encoding="utf-8",
)  # fmt: skip

VERB = "season-score"
SEED: list = []
RUNS = {
    "score": ["season-score", "--round-file", str(ROUND)],
    "compare": ["season-score", "--round-file", str(ROUND), "--compare"],
    "policies": ["season-score", "--policies"],
}
# No empty state: a round with no claims is a usage error (exit 2) before and after.
EMPTY = None
QUESTIONS = [
    {"run": "score", "q": "How many points does alice have in total?", "a": 4, "grade": "number"},
    {"run": "score", "q": "How many claims were left unscored?", "a": 1, "grade": "number"},
    {"run": "score", "q": "Which player's claim was unscored?", "a": "carol", "grade": "exact"},
    {"run": "compare", "q": "Which player ranks first under v2_aixcc?", "a": "bob", "grade": "exact"},
    {
        "run": "compare",
        "q": "Do the two policies rank the players in a different order? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
    {"run": "compare", "q": "What is bob's delta between the two policies?", "a": 4, "grade": "number"},
    {"run": "policies", "q": "Which scoring policy is the default?", "a": "v1_doc", "grade": "exact"},
]
