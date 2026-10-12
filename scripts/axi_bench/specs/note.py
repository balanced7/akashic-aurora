"""AXI bench spec: `note` -- write a durable note, read one back, miss one."""

VERB = "note"
SEED = [
    ["note", "bench", "--title", "where-we-are", "--note", "Wave 2 done; next: the payment refactor."],
]
RUNS = {
    "write": ["note", "alice", "--title", "where-we-are", "--note",
              "Wave 3 done; next: migrate the ledger table.", "--context", "decided at the Monday sync"],
    "get": ["note", "alice", "--get", "where-we-are"],
    "missing": ["note", "alice", "--get", "never-existed"],
}  # fmt: skip
EMPTY = None  # a write verb: the miss case is RUNS["missing"]
QUESTIONS = [
    {
        "run": "write",
        "q": "Did this note replace an earlier note with the same title? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
    {
        "run": "get",
        "q": "According to the note, what comes next? Answer in a few words.",
        "a": ["ledger table"],
        "grade": "contains",
    },
    {
        "run": "get",
        "q": "Where was this decided, according to the note's context?",
        "a": ["monday"],
        "grade": "contains",
    },
    {"run": "missing", "q": "Was a note found? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "missing",
        "q": "Which command lists the notes that do exist? Give the command only.",
        "a": ["notes"],
        "grade": "contains",
    },
]
