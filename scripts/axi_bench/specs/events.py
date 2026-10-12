"""AXI bench spec: `events` -- the raw event firehose (recent, search, one event)."""

LONG = (
    "migrated the lessons table to the v3 schema: renamed four columns, backfilled the scope field "
    + "for every row, rebuilt the keyword index and verified the counts match the old table. " * 4
)

VERB = "events"
SEED = [
    ["events", "--capture", "--kind", "deploy", "--summary", "deployed api v2 to staging", "--agent", "alice",
     "--track", "ops"],
    ["events", "--capture", "--kind", "test_run", "--summary", "ran suite: 3 failures in auth", "--agent", "bob"],
    ["events", "--capture", "--kind", "migration", "--summary", LONG, "--agent", "carol", "--track", "data"],
    ["events", "--capture", "--kind", "note", "--summary", "paused the release until the auth fix lands",
     "--agent", "alice"],
]  # fmt: skip
RUNS = {
    "recent": ["events"],
    "search": ["events", "--search", "auth failures"],
    "bob": ["events", "--agent", "dave"],
    "capped": ["events", "--limit", "2"],
}
EMPTY = ["events"]
QUESTIONS = [
    {"run": "recent", "q": "How many raw events does this output list?", "a": 4, "grade": "number"},
    {"run": "recent", "q": "Which agent recorded the deploy event?", "a": "alice", "grade": "exact"},
    {"run": "recent", "q": "Which track is the migration event on?", "a": "data", "grade": "exact"},
    {
        "run": "recent",
        "q": "Is the summary of the migration event shown in full? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "search",
        "q": "What exact command would show the full record of the top-ranked event? Give the command only.",
        "a": ["events", "--get", "event:events:raw:"],
        "grade": "contains",
    },
    {"run": "bob", "q": "How many events by agent dave are listed?", "a": 0, "grade": "number"},
    {
        "run": "capped",
        "q": "Does this output show every stored raw event, with none left out? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
]
