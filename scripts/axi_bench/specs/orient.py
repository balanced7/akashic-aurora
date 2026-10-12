"""AXI bench spec: `orient` -- one read-only scene: awareness landmarks plus a typed focus."""

VERB = "orient"
SEED = [
    ["bifrost-send", "alice", "tests are red on master", "--to", "bench", "--kind", "blocker"],
]
RUNS = {
    "ambient": ["orient"],
    "verb": ["orient", "verb:recall"],
    "bad": ["orient", "bogus:x"],
}
EMPTY = ["orient"]
QUESTIONS = [
    {"run": "ambient", "q": "How many landmarks does the scene contain in total?", "a": 4, "grade": "number"},
    {"run": "ambient", "q": "Which landmark is shown nearby, in focus?", "a": "bus", "grade": "exact"},
    {
        "run": "verb",
        "q": "What is the authority of the focus claim? Give the value only.",
        "a": "mechanical_source",
        "grade": "exact",
    },
    {"run": "verb", "q": "How many blind spots does the scene report?", "a": 2, "grade": "number"},
    {
        "run": "verb",
        "q": "What is the full command to return to ambient awareness? Give the command only.",
        "a": ["sweep", "bench"],
        "grade": "contains",
    },
    {"run": "bad", "q": "Did the command produce a scene? Answer yes or no.", "a": "no", "grade": "exact"},
]
