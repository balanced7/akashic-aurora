"""AXI bench spec: `delta` -- what moved since an agent's last boot."""

VERB = "delta"
SEED = [
    ["boot", "alice", "--task", "stamp the delta mark"],  # the first boot writes alice's mark
    ["note", "bench", "--title", "where-we-are", "--note", "Wave 3 done; next: the ledger table."],
]
RUNS = {"moved": ["delta", "alice"], "newborn": ["delta", "carol"]}
EMPTY = ["delta", "alice"]
QUESTIONS = [
    {
        "run": "moved",
        "q": "Have the project notes been updated since alice's last boot? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
    {
        "run": "moved",
        "q": "Which command shows the notes that changed? Give the command only.",
        "a": ["agent_cli.py notes"],
        "grade": "contains",
    },
    {
        "run": "moved",
        "q": "What exact command marks these changes as seen for alice? Give the command only.",
        "a": ["delta alice", "--ack"],
        "grade": "contains",
    },
    {"run": "newborn", "q": "Does carol have a delta mark yet? Answer yes or no.", "a": "no", "grade": "exact"},
]
