"""AXI bench spec: `recall-at` -- the few lessons and locks that matter for one action.

Lessons are seeded by agents other than `bench` on purpose: recall-at never echoes an agent's
own lessons back to it, and the bench asks as `bench`.
"""

BUS = "bus hangs at start restart embedded redis"

VERB = "recall-at"
SEED = [
    ["learn", "alice", "--experiment", "bus_restart", "--tried", "retried", "--result", "hung again",
     "--recommend", "Use when the bus hangs at start: restart the embedded redis before retrying.",
     "--category", "ops", "--success", "partial"],
    ["learn", "carol", "--experiment", "bus_hang_logs", "--tried", "restarted", "--result", "found it",
     "--recommend", "Use when the bus hangs at start: read the embedded redis log first.",
     "--category", "ops", "--success", "yes"],
    ["lock", "bob", "core/comm/bus.py"],
]  # fmt: skip
RUNS = {
    "cmd": ["recall-at", "--command", BUS],
    "cut": ["recall-at", "--command", BUS, "--limit", "1"],
    "path": ["recall-at", "--path", "core/comm/bus.py"],
    "none": ["recall-at", "--command", "zzzq qqqz"],
}
EMPTY = ["recall-at", "--command", "zzzq qqqz"]
QUESTIONS = [
    {"run": "cmd", "q": "Which agent wrote the bus_restart lesson?", "a": "alice", "grade": "exact"},
    {
        "run": "cmd",
        "q": "Did the bus_restart lesson's author report that it worked, partly worked, or is it unverified? "
        "Answer worked, partial or unverified.",
        "a": "partial",
        "grade": "exact",
    },
    {"run": "path", "q": "Which agent holds a lock on this path?", "a": "bob", "grade": "exact"},
    {"run": "cut", "q": "How many relevant lessons cleared the floor in total?", "a": 2, "grade": "number"},
    {"run": "none", "q": "How many relevant lessons were found?", "a": 0, "grade": "number"},
    {
        "run": "cut",
        "q": "What exact command shows the complete record of the lesson shown? Give the command only.",
        "a": ["--full", "learn:experiment:bus_restart"],
        "grade": "contains",
    },
]
