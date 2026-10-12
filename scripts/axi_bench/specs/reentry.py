"""AXI bench spec: `reentry` -- the operator re-entry render: what moved, one open door, your move.

Offline and fixed: --stale-ok skips the transcript ingest (the eye index stays the sandbox's
empty one), and --since pins the diff point to a moment the task ledger has rows after. The
ledger is the tree's own state/coord/tasks.json, identical on both sides. Commits come from
`git log`, which the exported before-tree cannot run, so no question asks about commits."""

SINCE = "2026-09-23T12:00:00+00:00"
VERB = "reentry"
SEED: list = []
RUNS = {
    "moved": ["reentry", "--stale-ok", "--since", SINCE],
    "quiet": ["reentry", "--stale-ok", "--since", "2099-01-01T00:00:00+00:00"],
}
EMPTY = ["reentry", "--stale-ok", "--since", "2099-01-01T00:00:00+00:00"]
QUESTIONS = [
    {"run": "moved", "q": "How many task-ledger rows moved since the diff point?", "a": 7, "grade": "number"},
    {"run": "moved", "q": "Which status did task T404 move to?", "a": "abandoned", "grade": "exact"},
    {"run": "moved", "q": "Which commit is task T406 tied to?", "a": "afe326ad", "grade": "exact"},
    {
        "run": "moved",
        "q": "Was an open door (a verbatim utterance of the operator) found? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "moved",
        "q": "What does the operator type to open task T405? Give the words only.",
        "a": ["approve T405"],
        "grade": "contains",
    },
    {"run": "quiet", "q": "Did any task-ledger rows move? Answer yes or no.", "a": "no", "grade": "exact"},
]
