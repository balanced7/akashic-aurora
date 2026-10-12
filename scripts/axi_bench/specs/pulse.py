"""AXI bench spec: `pulse` -- where pressure is building on the work lanes.

alice and bob each consume one message (which gives them a work-lane cursor), then eleven requests pile up
for alice: elevated pressure (10 or more). carol gets mail but never consumes: no lane, so a
legacy agent. EMPTY is the quiet fleet. Seats beat under an incarnation the spec names for the
sandboxed CLI, as the roster spec does."""

import os

os.environ.setdefault("BIFROST_INCARNATION", "benchseat-0001")

VERB = "pulse"
SEED = [
    # a lane cursor exists once a seat has consumed real mail, so each gets one message first
    ["bifrost-send", "bench", "hello alice", "--to", "alice", "--kind", "request"],
    ["bifrost-send", "bench", "hello bob", "--to", "bob", "--kind", "request"],
    ["bifrost-sync", "alice", "--consume"],
    ["bifrost-sync", "bob", "--consume"],
    *[["bifrost-send", "bench", f"request {i}", "--to", "alice", "--kind", "request"] for i in range(11)],
    ["bifrost-send", "bench", "a note for carol", "--to", "carol", "--kind", "request"],
]
RUNS = {"fleet": ["pulse"]}
EMPTY = ["pulse"]
QUESTIONS = [
    {"run": "fleet", "q": "Which agent has elevated pressure?", "a": "alice", "grade": "exact"},
    {"run": "fleet", "q": "How many messages are in alice's backlog?", "a": 11, "grade": "number"},
    {"run": "fleet", "q": "Is any agent in the critical zone? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "fleet",
        "q": "Which agents have no work lane? List them separated by commas.",
        "a": ["bench", "carol"],
        "grade": "set",
    },
    {
        "run": "fleet",
        "q": "What exact command diagnoses the agent under the most pressure? Give the command only.",
        "a": ["unwedge", "alice"],
        "grade": "contains",
    },
]
