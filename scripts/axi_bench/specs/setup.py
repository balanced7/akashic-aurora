"""AXI bench spec: `setup` -- the onboarding sequence, run non-interactively as a dry run.

Only `--yes --dry-run` is benched: setup otherwise writes harness settings, the operator file and
the repo's git hooks, and asks questions on stdin. Hooks are aimed at a throwaway project
directory with --scope project, because a user-scope Claude install compares against the
checkout's own settings files (the one-surface rule), which differ between the two trees.
"""

import tempfile

PROJECT = tempfile.mkdtemp(prefix="axi-setup-")

VERB = "setup"
SEED = []
RUNS = {
    "dry": [
        "setup", "--yes", "--dry-run", "--harness", "claude", "--harness", "codex", "--scope", "project",
        "--project", PROJECT, "--agent-id", "benchseat", "--operator", "Bench Person <bench@example.com>",
    ],
}  # fmt: skip
EMPTY = None
QUESTIONS = [
    {"run": "dry", "q": "Did this run write anything to disk? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "dry",
        "q": "Which agent id would the Claude Code seat write memory as?",
        "a": "benchseat",
        "grade": "exact",
    },
    {"run": "dry", "q": "How many codex hooks would be registered?", "a": 5, "grade": "number"},
    {
        "run": "dry",
        "q": "Whose name would go on commits that agents make? Give the name only, without the email.",
        "a": "Bench Person",
        "grade": "exact",
    },
    {
        "run": "dry",
        "q": "What command changes, later, whose name goes on agent commits? Give the command only.",
        "a": ["setup", "--operator"],
        "grade": "contains",
    },
    {
        "run": "dry",
        "q": "Would the akashic-aurora MCP tools be registered user-wide by this run? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
]
