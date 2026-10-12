"""AXI bench spec: `unwedge` -- why is this agent stuck, in one verdict.

alice beats a live seat through `bifrost-sync` (the spec names an incarnation for the sandboxed
CLI, as the roster spec does); carol has mail waiting and no seat at all.

EMPTY is left out: an agent the quiet fleet has never seen reads "down" (no runner) and exits 1,
before and after, by design -- the verb's exit code says whether the agent is stuck."""

import os

os.environ.setdefault("BIFROST_INCARNATION", "benchseat-0001")

VERB = "unwedge"
SEED = [
    ["bifrost-sync", "alice"],
    ["bifrost-send", "bench", "please review the uploader retry", "--to", "carol", "--kind", "request"],
]
RUNS = {
    "carol": ["unwedge", "carol"],
    "alice": ["unwedge", "alice"],
}
EMPTY = None
QUESTIONS = [
    {"run": "carol", "q": "What is carol's status, in one word?", "a": "down", "grade": "exact"},
    {"run": "carol", "q": "How many messages wait in carol's work backlog?", "a": 1, "grade": "number"},
    {
        "run": "carol",
        "q": "What command does the output recommend running? Give the command only.",
        "a": ["bifrost_runner_deepseek.py", "--agent carol"],
        "grade": "contains",
    },
    {"run": "alice", "q": "Is a runner process alive for alice? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "alice",
        "q": "Does the output report any page-grade findings for alice? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
]
