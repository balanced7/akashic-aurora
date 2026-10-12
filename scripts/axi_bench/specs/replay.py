"""AXI bench spec: `replay` -- candidate harnesses and the replay runner's offline paths.

`replay run` launches a real harness against a scenario and spends model budget, so it is never
run here. The runs cover the candidate list (seeded with `replay new`, which only writes a card),
a run asked for with missing arguments, and the refusal of the live Redis db."""

VERB = "replay"
SEED = [
    ["replay", "new", "--candidate", "opus-high", "--harness", "claude-code", "--model", "claude-opus-5-5",
     "--effort", "high", "--hypothesis", "more effort fixes more scenarios"],
    ["replay", "new", "--candidate", "codex-low", "--harness", "codex-cli", "--model", "gpt-5", "--effort", "low",
     "--parent", "baseline"],
]  # fmt: skip
RUNS = {
    "candidates": ["replay", "candidates"],
    "live_db": ["replay", "run", "--candidate", "opus-high", "--scenario", "T1-abc", "--redis-db", "0"],
    "missing": ["replay", "run", "--candidate", "opus-high"],
}
EMPTY = None  # `baseline` always exists: the list is never empty
QUESTIONS = [
    {"run": "candidates", "q": "How many candidate harnesses are listed?", "a": 2, "grade": "number"},
    {"run": "candidates", "q": "Which harness does the candidate codex-low use?", "a": "codex-cli", "grade": "exact"},
    {"run": "candidates", "q": "What effort level is opus-high set to?", "a": "high", "grade": "exact"},
    {"run": "live_db", "q": "Did the replay run start? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "live_db",
        "q": "Which Redis db number should be passed instead so the run is allowed? Give the number only.",
        "a": 15,
        "grade": "number",
    },
    {
        "run": "missing",
        "q": "Which flag is missing from this replay run command? Give the flag only.",
        "a": "--scenario",
        "grade": "contains",
    },
]
