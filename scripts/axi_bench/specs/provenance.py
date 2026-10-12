"""AXI bench spec: `provenance` -- a session's harness, model, effort and environment record."""

VERB = "provenance"
SEED = [["provenance", "--session", "s-bench-1", "--agent", "alice"]]
RUNS = {
    "show": ["provenance", "--session", "s-bench-1"],
    "none": ["provenance"],
}
# No empty-store run: with no session id there is no record to show, and that stays an error
# (exit 1) by design, so the "explicit zero with exit 0" check does not apply.
EMPTY = None
QUESTIONS = [
    {"run": "show", "q": "Which agent id does this session record name?", "a": "alice", "grade": "exact"},
    {"run": "show", "q": "Which harness did this session run in?", "a": "shell", "grade": "exact"},
    {
        "run": "show",
        "q": "Which fields of the record are still unknown? List the field names separated by commas.",
        "a": ["harness_version", "model", "effort"],
        "grade": "set",
    },
    {"run": "none", "q": "Was a provenance record found? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "none",
        "q": "What exact command would show the provenance record of a session whose id you know? "
        "Give the command only.",
        "a": ["provenance", "--session"],
        "grade": "contains",
    },
]
