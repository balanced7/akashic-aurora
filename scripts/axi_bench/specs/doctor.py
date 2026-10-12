"""AXI bench spec: `doctor` -- fleet liveness findings and the infrastructure services.

Two live seats beat through `bifrost-sync` (the spec names an incarnation for the sandboxed CLI,
as the roster spec does), and mail to carol, who has no seat, gives the doctor an agent with a
durable inbox and nobody consuming it. EMPTY is the quiet fleet: no seat, no mail."""

import os

os.environ.setdefault("BIFROST_INCARNATION", "benchseat-0001")

VERB = "doctor"
SEED = [
    ["bifrost-sync", "alice"],
    ["bifrost-sync", "bob"],
    ["bifrost-send", "bench", "please review the uploader retry", "--to", "carol", "--kind", "request"],
]
RUNS = {"fleet": ["doctor"]}
EMPTY = ["doctor"]
QUESTIONS = [
    {"run": "fleet", "q": "How many findings did the doctor report about agents?", "a": 1, "grade": "number"},
    {"run": "fleet", "q": "Which agent has a finding?", "a": "carol", "grade": "exact"},
    {"run": "fleet", "q": "Is the redis service running? Answer yes or no.", "a": "yes", "grade": "exact"},
    {
        "run": "fleet",
        "q": "Which services are down? List their names separated by commas.",
        "a": ["ui:8787", "daemon"],
        "grade": "set",
    },
    {
        "run": "fleet",
        "q": "What command does the doctor suggest for carol's unread mail? Give the command only.",
        "a": ["bifrost-skip-to-now", "carol"],
        "grade": "contains",
    },
    {"run": "fleet", "q": "How many agents did the doctor examine?", "a": 6, "grade": "number"},
]
