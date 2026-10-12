"""AXI bench spec: `aurora` with no verb -- the home view (AXI section 8, content first)."""

VERB = ""
SEED = [
    ["learn", "bench", "--experiment", "e1", "--tried", "a", "--result", "b"],
    ["learn", "bench", "--experiment", "e2", "--tried", "a", "--result", "b"],
    ["learn", "bench", "--experiment", "e3", "--tried", "a", "--result", "b"],
]
RUNS = {"home": []}
EMPTY = None
QUESTIONS = [
    {"run": "home", "q": "How many lessons are stored in memory?", "a": 3, "grade": "number"},
    {"run": "home", "q": "Which agent id is this session using?", "a": "bench", "grade": "exact"},
    {
        "run": "home",
        "q": "What is the full command to load an agent's startup context? Give the command only.",
        "a": ["boot", "--task"],
        "grade": "contains",
    },
    {
        "run": "home",
        "q": "What is the full command to search past lessons? Give the command only.",
        "a": ["recall"],
        "grade": "contains",
    },
]
