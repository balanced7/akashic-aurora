"""AXI bench spec: `task` -- the governed task ledger (list, next, a mutation, a refusal).

The ledger file lives in the sandbox (the harness points AKASHIC_TASKS_PATH there), so the seed
walks the real lifecycle without touching the checkout's state/coord/tasks.json."""

VERB = "task"
SEED = [
    ["task", "propose", "Fix the login redirect", "--files", "core/auth.py", "--by", "bench"],
    ["task", "propose", "Write the setup docs", "--by", "bench"],
    ["task", "propose", "Retire the old poller", "--by", "bench"],
    ["task", "propose", "Speed up boot", "--by", "bench"],
    ["task", "approve", "T004"],
    ["task", "claim", "T004", "--by", "bob"],
    ["task", "start", "T004", "--by", "bob"],
    ["task", "verify", "T004"],
    ["task", "done", "T004", "--commit", "deadbee1", "--verified-by", "pytest"],
    ["task", "approve", "T001"],
    ["task", "claim", "T001", "--by", "alice"],
    ["task", "start", "T001", "--by", "alice"],
    ["task", "approve", "T002"],
]
# Runs share the seeded ledger and run in order; `refused` approves a task that is already
# in progress, which the ledger refuses.
RUNS = {
    "list": ["task", "list"],
    "next": ["task", "next"],
    "propose": ["task", "propose", "Add a retry to the uploader", "--by", "bench"],
    "refused": ["task", "approve", "T001"],
}
EMPTY = ["task", "list"]
QUESTIONS = [
    {"run": "list", "q": "How many tasks are in the ledger in total?", "a": 4, "grade": "number"},
    {"run": "list", "q": "Which agent owns the task that is in progress?", "a": "alice", "grade": "exact"},
    {"run": "list", "q": "Which task is done? Answer with its id.", "a": "T004", "grade": "exact"},
    {
        "run": "next",
        "q": "Which task can be claimed right now? Answer with its id, or none.",
        "a": "none",
        "grade": "exact",
    },
    {"run": "propose", "q": "What id did the new task get?", "a": "T005", "grade": "exact"},
    {
        "run": "propose",
        "q": "What exact command moves the new task to its next lifecycle step? Give the command only.",
        "a": ["approve", "T005"],
        "grade": "contains",
    },
    {"run": "refused", "q": "Did the command succeed? Answer yes or no.", "a": "no", "grade": "exact"},
]
