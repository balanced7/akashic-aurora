"""AXI bench spec: `timeline` -- one chronological view across domains.

timeline also reads the CHECKOUT it runs from (git history, file mtimes, state/coord/tasks.json),
and the two sides of the bench are different checkouts: the baseline is a fresh export with no
.git, whose files (.aurora-world, state/redis-backend) are written moments before it runs. So the
window is kept to 18 seconds (--hours 0.005) and every question is about the events domain,
which both sides read from the same seeded sandbox; row totals that include files or git would
differ between the sides for reasons that have nothing to do with the output format.
"""

VERB = "timeline"
SEED = [
    ["events", "--capture", "--kind", "deploy", "--summary", "deployed api v2 to staging", "--agent", "alice"],
    ["events", "--capture", "--kind", "test_run", "--summary", "ran suite: 3 failures in auth", "--agent", "bob"],
    ["events", "--capture", "--kind", "rollback", "--summary", "rolled api back to v1", "--agent", "alice"],
]
RUNS = {
    "window": ["timeline", "--hours", "0.005"],
    "cut": ["timeline", "--hours", "0.005", "--limit", "1"],
}
EMPTY = ["timeline", "--hours", "0.005"]
QUESTIONS = [
    {"run": "window", "q": "Which actor recorded the test_run row?", "a": "bob", "grade": "exact"},
    {"run": "window", "q": "How many rows came from the events domain?", "a": 3, "grade": "number"},
    {
        "run": "window",
        "q": "Of the rows from the events domain, what is the kind of the most recent one?",
        "a": "rollback",
        "grade": "exact",
    },
    {
        "run": "cut",
        "q": "Does this output list every row in the time window? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {"run": "cut", "q": "How many rows from the events domain fall in the time window?", "a": 3, "grade": "number"},
]
