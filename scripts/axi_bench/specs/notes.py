"""AXI bench spec: `notes` -- list the durable project notes."""

DOCKET = (
    "Open docket: (1) migrate the ledger table to the new schema, (2) retire the legacy bus lane once "
    "the dual-write window closes, (3) re-run the suite baseline after both, (4) write up the outcome."
)

VERB = "notes"
SEED = [
    ["note", "bench", "--title", "where-we-are", "--note", "Wave 2 done; next: the payment refactor."],
    ["note", "bench", "--title", "where-we-are", "--note", "Wave 3 done; next: migrate the ledger table."],
    ["note", "bench", "--title", "open-docket", "--note", DOCKET],
    ["note", "bench", "--title", "release-plan", "--note", "Ship 2.0 on Friday after the soak."],
]
RUNS = {"list": ["notes"], "all": ["notes", "--all"]}
EMPTY = ["notes"]
QUESTIONS = [
    {"run": "list", "q": "How many active notes are there?", "a": 3, "grade": "number"},
    {
        "run": "list",
        "q": "Is the open-docket note shown in full here? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "list",
        "q": "What exact command prints the full open-docket note? Give the command only.",
        "a": ["--get", "open-docket"],
        "grade": "contains",
    },
    {"run": "all", "q": "How many notes are listed, superseded ones included?", "a": 4, "grade": "number"},
    {
        "run": "all",
        "q": "Which note title has an older, superseded version? Give the title only.",
        "a": "where-we-are",
        "grade": "exact",
    },
]
