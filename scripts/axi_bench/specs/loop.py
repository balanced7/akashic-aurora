"""AXI bench spec: `loop` -- the candidate archive and the proposer loop, offline paths only.

`loop run` proposes and replays candidates with real models and spends money, so it only runs
here without --daily-usd, which it refuses before doing anything. Candidates are seeded with
`replay new` (it writes a card), in a parent chain baseline <- v1 <- v2."""

VERB = "loop"
SEED = [
    ["replay", "new", "--candidate", "baseline", "--harness", "claude-code"],
    ["replay", "new", "--candidate", "v1", "--harness", "claude-code", "--parent", "baseline",
     "--hypothesis", "a test-first skill raises the pass rate"],
    ["replay", "new", "--candidate", "v2", "--harness", "claude-code", "--parent", "v1",
     "--hypothesis", "a shorter CLAUDE.md costs fewer tokens"],
]  # fmt: skip
RUNS = {
    "status": ["loop", "status"],
    "archive": ["loop", "archive"],
    "lineage": ["loop", "lineage", "--candidate", "v2"],
    "run": ["loop", "run"],
}
EMPTY = ["loop", "archive"]
QUESTIONS = [
    {"run": "archive", "q": "How many candidates are in the archive?", "a": 3, "grade": "number"},
    {"run": "archive", "q": "Which candidate is the parent of v2?", "a": "v1", "grade": "exact"},
    {"run": "lineage", "q": "Which candidate is the root ancestor of v2?", "a": "baseline", "grade": "exact"},
    {"run": "status", "q": "How much money, in USD, has the loop spent today?", "a": 0, "grade": "number"},
    {
        "run": "run",
        "q": "Which flag must be added for `loop run` to start? Give the flag only.",
        "a": "--daily-usd",
        "grade": "contains",
    },
]
