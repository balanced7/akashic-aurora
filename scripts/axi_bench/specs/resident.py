"""AXI bench spec: `resident` -- the callsign ceremony's designations, postings and roles.

Everything lives in the sandbox store: lessons as receipts, a nomination, a ratification, a
posting and a role assignment, all made through the CLI.
"""

VERB = "resident"
SEED = [
    ["learn", "alice", "--experiment", "alice_port_fix", "--tried", "a", "--result", "b", "--recommend", "check"],
    ["learn", "carol", "--experiment", "carol_note", "--tried", "a", "--result", "b"],
    ["resident", "nominate", "alice", "--callsign", "Lantern", "--receipt", "alice_port_fix", "--by", "bob",
     "--family", "scouts", "--team", "blue", "--number", "7"],
    ["resident", "ratify", "alice", "--callsign", "Lantern", "--by", "operator"],
    ["resident", "nominate", "carol", "--callsign", "Ember", "--receipt", "carol_note", "--by", "bob"],
    ["resident", "assign", "alice", "--role", "Jester", "--side", "Red", "--exercise", "ex7", "--by", "bob"],
]  # fmt: skip
RUNS = {
    "show": ["resident", "show", "alice"],
    "pending": ["resident", "show", "carol"],
    "roster": ["resident", "roster"],
    "roles": ["resident", "roles"],
    "refused": ["resident", "nominate", "dave", "--callsign", "Moss", "--receipt", "alice_port_fix", "--by", "bob"],
}
EMPTY = ["resident", "roster"]
QUESTIONS = [
    {"run": "show", "q": "What is alice's callsign?", "a": "Lantern", "grade": "exact"},
    {"run": "show", "q": "Which role is alice operating as right now?", "a": "Jester", "grade": "exact"},
    {"run": "show", "q": "Who ratified alice's callsign?", "a": "operator", "grade": "exact"},
    {
        "run": "pending",
        "q": "Is carol's callsign ratified yet? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "pending",
        "q": "What command would ratify carol's callsign? Give the command only.",
        "a": ["resident ratify carol", "--callsign ember"],
        "grade": "contains",
    },
    {"run": "roster", "q": "How many residents are on the roster?", "a": 2, "grade": "number"},
    {"run": "refused", "q": "Did the nomination succeed? Answer yes or no.", "a": "no", "grade": "exact"},
]
