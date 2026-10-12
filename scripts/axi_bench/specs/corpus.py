"""AXI bench spec: `corpus` -- the meta-harness task corpus, on an empty store.

Scenarios are mined from the task ledger, and the bench sandbox cannot isolate that ledger
(it lives beside the code unless AKASHIC_TASKS_PATH says otherwise), so nothing is mined here:
the runs cover what an agent sees before the corpus has anything -- status, list, a missing
scenario, and an archive pass over the sandbox's empty home (no transcripts to copy)."""

VERB = "corpus"
SEED = []
RUNS = {
    "status": ["corpus", "status"],
    "list": ["corpus", "list"],
    "missing": ["corpus", "show", "T999-deadbeef"],
    "archive": ["corpus", "archive"],
}
EMPTY = ["corpus", "list"]
QUESTIONS = [
    {"run": "status", "q": "How many scenarios does the corpus hold?", "a": 0, "grade": "number"},
    {
        "run": "list",
        "q": "What command should be run next to put scenarios into the corpus? Give the command only.",
        "a": ["corpus mine"],
        "grade": "contains",
    },
    {"run": "missing", "q": "Does the scenario T999-deadbeef exist? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "archive", "q": "How many transcripts were archived by this run?", "a": 0, "grade": "number"},
    {"run": "archive", "q": "What is the archive's size cap, in MB?", "a": 2048, "grade": "number"},
]
