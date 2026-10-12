"""AXI bench spec: `compress` -- harness compression, offline paths only.

`compress run` replays candidates with real models and is capped by --max-runs, so it only runs
here without that flag, which it refuses first. `pieces` reads the checkout's own harness files
(AGENTS.md sections, skills, hooks); `telemetry` reads replay runs, of which the sandbox has
none."""

VERB = "compress"
SEED = []
RUNS = {
    "pieces": ["compress", "pieces"],
    "telemetry": ["compress", "telemetry", "--candidate", "baseline", "--scenario", "T1-abc"],
    "run": ["compress", "run", "--candidate", "baseline", "--scenario", "T1-abc"],
}
EMPTY = ["compress", "telemetry", "--candidate", "baseline", "--scenario", "T1-abc"]
QUESTIONS = [
    {"run": "pieces", "q": "How many switchable harness pieces are there in total?", "a": 20, "grade": "number"},
    {"run": "pieces", "q": "How many of the pieces are skills?", "a": 5, "grade": "number"},
    {"run": "telemetry", "q": "How many replay runs were read?", "a": 0, "grade": "number"},
    {
        "run": "run",
        "q": "Which flag is missing from this compress run command? Give the flag only.",
        "a": "--max-runs",
        "grade": "contains",
    },
]
