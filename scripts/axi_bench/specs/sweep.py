"""AXI bench spec: `sweep` -- the awareness snapshot of one seat: bus, bench, route, moved."""

VERB = "sweep"
SEED = [
    ["bifrost-send", "alice", "please review core/a.py", "--to", "bench"],
    ["bifrost-send", "alice", "tests are red on master", "--to", "bench", "--kind", "blocker"],
    ["bifrost-send", "carol", "fyi: merged the docs", "--to", "bench"],
]
RUNS = {"bench": ["sweep", "bench"]}
EMPTY = ["sweep", "bench"]
QUESTIONS = [
    {"run": "bench", "q": "How many bus messages are pending for the seat?", "a": 3, "grade": "number"},
    {"run": "bench", "q": "How many of the pending messages need attention?", "a": 1, "grade": "number"},
    {
        "run": "bench",
        "q": "Is the observed seat attended by a live session right now? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "bench",
        "q": "Is it known whether anything moved since the seat's last mark? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "bench",
        "q": "What is the full command to read the pending messages? Give the command only.",
        "a": ["bifrost-sync bench"],
        "grade": "contains",
    },
]
