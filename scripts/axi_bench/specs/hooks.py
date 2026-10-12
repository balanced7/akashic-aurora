"""AXI bench spec: `hooks` -- which harness config files carry Aurora's hooks, and changing them.

Every write lands in a throwaway project directory made here and in the sandbox HOME the bench
gives each run, never in this checkout's or the real home's settings: project-scope installs name
--project explicitly, because a user-scope install compares against the cwd's project files
(the one-surface rule) and the cwd is the checkout.
"""

import tempfile

PROJECT = tempfile.mkdtemp(prefix="axi-hooks-")
BARE = tempfile.mkdtemp(prefix="axi-hooks-empty-")

VERB = "hooks"
SEED = [
    ["hooks", "install", "--harness", "claude", "--scope", "project", "--project", PROJECT],
    ["hooks", "install", "--harness", "codex", "--scope", "project", "--project", PROJECT],
    ["hooks", "disable", "--harness", "codex", "--scope", "project", "--project", PROJECT],
    ["hooks", "enroll", "--project", PROJECT],
]
RUNS = {
    "status": ["hooks", "status", "--project", PROJECT],
    "dry": ["hooks", "install", "--harness", "cursor", "--scope", "project", "--project", PROJECT, "--dry-run"],
}
EMPTY = ["hooks", "status", "--project", BARE]
QUESTIONS = [
    {
        "run": "status",
        "q": "How many Aurora hooks are installed in the claude project settings file?",
        "a": 10,
        "grade": "number",
    },
    {
        "run": "status",
        "q": "Which harness has its Aurora hooks switched off (disabled)? Give the harness name only.",
        "a": "codex",
        "grade": "exact",
    },
    {"run": "status", "q": "How many codex hooks are disabled?", "a": 5, "grade": "number"},
    {
        "run": "status",
        "q": "What command turns the disabled hooks back on? Give the command only.",
        "a": ["hooks enable", "--harness codex", "--scope project"],
        "grade": "contains",
    },
    {
        "run": "status",
        "q": "How many projects are enrolled (where the hooks speak up)?",
        "a": 1,
        "grade": "number",
    },
    {
        "run": "dry",
        "q": "How many cursor hooks would this install add?",
        "a": 6,
        "grade": "number",
    },
    {
        "run": "dry",
        "q": "Did this command write anything to disk? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
]
