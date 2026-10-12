"""AXI bench spec: `flightdeck` -- the cockpit one-pager over doctor, pulse and the rest.

Same fleet as the doctor spec: two live seats beat through `bifrost-sync` (the spec names an
incarnation for the sandboxed CLI), and carol has mail waiting and no seat. The commits section
reads the code tree's git log, which the exported before-tree does not have, so no question
asks about commits."""

import os

os.environ.setdefault("BIFROST_INCARNATION", "benchseat-0001")

VERB = "flightdeck"
SEED = [
    ["bifrost-sync", "alice"],
    ["bifrost-sync", "bob"],
    ["bifrost-send", "bench", "please review the uploader retry", "--to", "carol", "--kind", "request"],
]
RUNS = {
    "fleet": ["flightdeck"],
    "carol": ["flightdeck", "--agent", "carol"],
}
EMPTY = ["flightdeck"]
QUESTIONS = [
    {"run": "fleet", "q": "How many agents does the flightdeck list?", "a": 6, "grade": "number"},
    {"run": "fleet", "q": "Does carol have a work lane? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "fleet", "q": "How many locks does alice hold?", "a": 0, "grade": "number"},
    {"run": "carol", "q": "What is carol's status in the detail section, in one word?", "a": "down", "grade": "exact"},
    {
        "run": "fleet",
        "q": "What command shows the full detail for one agent? Give the command only.",
        "a": ["flightdeck", "--agent"],
        "grade": "contains",
    },
]
