"""AXI bench spec: `boot` -- an agent's startup context (lessons, notes, handoff, locks)."""

VERB = "boot"
SEED = [
    ["learn", "bench", "--experiment", "port_clash", "--tried", "ran the suite", "--result", "hung at start",
     "--recommend", "Use when tests hang at start: check that port 16379 is free first.", "--category",
     "performance", "--success", "yes"],
    ["learn", "bench", "--experiment", "git_blanket_staging", "--tried", "git add -A", "--result", "staged a secret",
     "--recommend", "Stage explicit paths, never git add -A.", "--category", "correction", "--success", "no"],
    ["note", "bench", "--title", "where-we-are", "--note",
     "Wave 3 of the payment refactor is done; next: migrate the ledger table."],
    ["handoff", "bench", "--to", "alice", "--task", "finish the ledger migration", "--note",
     "schema is done, the data copy is pending"],
    ["lock", "bob", "core/ledger.py", "--ttl", "600"],
]  # fmt: skip
RUNS = {"boot": ["boot", "alice", "--task", "tests hang at start"]}
EMPTY = ["boot", "alice"]
QUESTIONS = [
    {"run": "boot", "q": "Which port should be checked when tests hang at start?", "a": 16379, "grade": "number"},
    {"run": "boot", "q": "Which agent left alice a handoff?", "a": "bench", "grade": "exact"},
    {"run": "boot", "q": "Which file is locked by bob?", "a": "core/ledger.py", "grade": "exact"},
    {
        "run": "boot",
        "q": "According to the where-we-are note, what comes next? Answer in a few words.",
        "a": ["ledger table"],
        "grade": "contains",
    },
    {"run": "boot", "q": "How many lessons does this startup context carry?", "a": 2, "grade": "number"},
    {
        "run": "boot",
        "q": "What is the full command alice would run to record a new lesson? Give the command only.",
        "a": ["learn alice", "--experiment"],
        "grade": "contains",
    },
]
