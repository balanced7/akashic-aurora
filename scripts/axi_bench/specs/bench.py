"""AXI bench spec: `bench` -- the S0 triage bench (park / unpark / list stale asks).

Not the AXI bench harness: this verb bottoms a stale ask to a durable per-agent bench. Parking
takes an inbox stream id, which the seed cannot know in advance, so the bench measures the empty
listing and the error paths; the listing with parked asks, park and unpark receipts are pinned
in tests/test_axi_bench.py.
"""

VERB = "bench"
SEED = [["bifrost-send", "alice", "please review core/a.py", "--to", "bench", "--kind", "request",
         "--expect-reply-within", "0"]]  # fmt: skip
RUNS = {
    "list": ["bench", "bench"],
    "park_missing": ["bench", "bench", "park", "9999999999999-0"],
    "park_noref": ["bench", "bench", "park"],
    "unpark_missing": ["bench", "bench", "unpark", "abcdef123456"],
}
EMPTY = ["bench", "bench"]
QUESTIONS = [
    {"run": "list", "q": "How many asks are parked on bench's triage bench?", "a": 0, "grade": "number"},
    {"run": "park_missing", "q": "Was the message parked? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "park_noref", "q": "What must be added to this command for park to work? Answer in a few words.",
     "a": ["stream id"], "grade": "contains"},
    {"run": "unpark_missing", "q": "Was a parked ask with that id found on the bench? Answer yes or no.", "a": "no", "grade": "exact"},
]  # fmt: skip
