"""AXI bench spec: `boop` -- the smallest verb in the house: zero arguments, always answered."""

VERB = "boop"
SEED = [
    ["bifrost-send", "alice", "tests are red on master", "--to", "bench", "--kind", "blocker"],
]
RUNS = {
    "boop": ["boop"],
    "surface": ["boop", "--surface"],
}
EMPTY = None  # a boop has no empty state: it is always answered
QUESTIONS = [
    {"run": "boop", "q": "Was the boop received? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "boop", "q": "How was the boop adjudicated? Give one word.", "a": "useful", "grade": "exact"},
    {"run": "surface", "q": "How many bus messages are pending for the seat?", "a": 1, "grade": "number"},
    {
        "run": "surface",
        "q": "What is the full command to read the pending messages? Give the command only.",
        "a": ["bifrost-sync bench"],
        "grade": "contains",
    },
]
