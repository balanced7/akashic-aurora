"""AXI bench spec: `handoff` -- write a briefing for another agent, list the ones addressed to one."""

VERB = "handoff"
SEED = [
    ["handoff", "bob", "--to", "alice", "--task", "review the ledger migration PR", "--note", "CI is green"],
    ["handoff", "carol", "--to", "alice", "--task", "rotate the staging keys"],
]
RUNS = {
    "write": ["handoff", "bench", "--to", "alice", "--task", "finish the ledger migration", "--note",
              "schema done, data copy pending", "--blocker", "staging DB is read-only || waiting on DBA"],
    "list": ["handoff", "alice", "--list"],
    "none": ["handoff", "dave", "--list"],
}  # fmt: skip
EMPTY = ["handoff", "dave", "--list"]
QUESTIONS = [
    {"run": "write", "q": "Which agent will receive this handoff?", "a": "alice", "grade": "exact"},
    {"run": "write", "q": "How many blockers were flagged with the handoff?", "a": 2, "grade": "number"},
    {
        "run": "write",
        "q": "When will the receiving agent see this briefing? Answer in a few words.",
        "a": ["boot"],
        "grade": "contains",
    },
    {"run": "list", "q": "How many handoffs are addressed to alice?", "a": 3, "grade": "number"},
    {"run": "list", "q": "Who asked alice to rotate the staging keys?", "a": "carol", "grade": "exact"},
    {"run": "none", "q": "How many handoffs are addressed to dave?", "a": 0, "grade": "number"},
]
