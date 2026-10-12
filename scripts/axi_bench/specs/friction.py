"""AXI bench spec: `friction` -- the collaboration tax of one seat's asks.

The seed sends four directed requests from `bench` (each arms an expectation), two of the peers
reply, and `bifrost-sync` sweeps the replies into answered episodes. Nothing dies: a dead
episode takes three redrives of at least 30 seconds each, too slow for a bench.
"""

# The verb with its required agent id: the conformance checks append a bogus flag to this, and
# without the positional argparse reports the missing agent id before it ever sees the flag.
VERB = "friction bench"
SEED = [
    ["bifrost-send", "bench", "please review the parser change", "--to", "alice", "--kind", "request"],
    ["bifrost-send", "bench", "status of T12?", "--to", "bob", "--kind", "request"],
    ["bifrost-send", "bench", "can you rerun the suite", "--to", "carol", "--kind", "request"],
    ["bifrost-send", "bench", "is the bus up on your side", "--to", "dave", "--kind", "request"],
    ["bifrost-send", "alice", "looks good", "--to", "bench", "--kind", "reply"],
    ["bifrost-send", "carol", "suite is green", "--to", "bench", "--kind", "reply"],
    ["bifrost-sync", "bench"],
]
RUNS = {"bench": ["friction", "bench"]}
EMPTY = ["friction", "bench"]
QUESTIONS = [
    {"run": "bench", "q": "How many of bench's asks are still open?", "a": 2, "grade": "number"},
    {"run": "bench", "q": "How many of bench's asks were answered?", "a": 2, "grade": "number"},
    {
        "run": "bench",
        "q": "Which peers still have an open ask from bench? List them separated by commas.",
        "a": ["bob", "dave"],
        "grade": "set",
    },
    {"run": "bench", "q": "What is the dead rate, as a percentage?", "a": 0, "grade": "number"},
    {"run": "bench", "q": "Did any ask die? Answer yes or no.", "a": "no", "grade": "exact"},
]
