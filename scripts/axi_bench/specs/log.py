"""AXI bench spec: `log` -- record a narrative beat."""

VERB = "log"
SEED = []
RUNS = {
    "ok": ["log", "decision", "--summary", "picked Postgres over SQLite for the ledger", "--source", "bench:design"],
    "bare": ["log", "note"],
}
EMPTY = None  # a write verb: there is no empty listing to state
QUESTIONS = [
    {"run": "ok", "q": "Was the beat recorded? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "ok", "q": "What kind of beat was recorded? Give the kind only.", "a": "decision", "grade": "exact"},
    {
        "run": "ok",
        "q": "Which database was picked for the ledger, according to the beat?",
        "a": ["postgres"],
        "grade": "contains",
    },
    {
        "run": "bare",
        "q": "Did the caller give this beat a real summary? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
]
