"""AXI bench spec: `glance program` -- the read-only task-ledger projection.

`glance` reads the git-durable task ledger beside the code (state/coord/tasks.json), not the
sandbox's AKASHIC_TASKS_PATH, so the "before" and "after" trees would each read their own copy.
Every run therefore names a fixture ledger with the (hidden, long-standing) --ledger-path flag:
five tasks written here at import, one per attention class, plus an empty ledger for the empty
state. Both are read-only to the verb.
"""

import json
import tempfile
from pathlib import Path

# A fixed name, not mkdtemp: the path is part of the command the report and the CLI reference
# print, and a random one would change them on every run.
_DIR = Path(tempfile.gettempdir()) / "axi-bench-glance"
_DIR.mkdir(exist_ok=True)
LEDGER = _DIR / "tasks.json"
EMPTY_LEDGER = _DIR / "empty.json"
LEDGER.write_text(
    json.dumps(
        {
            "seq": 5,
            "tasks": [
                {"id": "T901", "title": "Fence the migration path", "status": "in_progress", "owner": "kimi",
                 "deps": [], "files": ["core/a.py"], "arc": "A3"},
                {"id": "T902", "title": "Retire the old bridge", "status": "blocked", "owner": "claude",
                 "deps": ["T901"], "files": []},
                {"id": "T903", "title": "Write the release notes", "status": "proposed", "owner": "", "deps": [],
                 "files": []},
                {"id": "T904", "title": "Measure the recall latency", "status": "done", "owner": "deepseek",
                 "deps": [], "files": [], "commit": "abc1234"},
                {"id": "T905", "title": "Approve the new seat", "status": "approved", "owner": "claude", "deps": [],
                 "files": []},
            ],
        }
    ),
    encoding="utf-8",
)  # fmt: skip
EMPTY_LEDGER.write_text(json.dumps({"seq": 0, "tasks": []}), encoding="utf-8")

VERB = "glance program"  # the leaf: `glance` itself hands its flags to its projections
SEED: list = []
RUNS = {
    "snapshot": ["glance", "program", "--ledger-path", str(LEDGER)],
    "cut": ["glance", "program", "--ledger-path", str(LEDGER), "--max-items", "2"],
    "brief": ["glance", "program", "--ledger-path", str(LEDGER), "--brief"],
    "missing": ["glance", "program", "--ledger-path", str(_DIR / "nope.json")],
}
EMPTY = ["glance", "program", "--ledger-path", str(EMPTY_LEDGER)]
QUESTIONS = [
    {"run": "snapshot", "q": "How many tasks need attention?", "a": 1, "grade": "number"},
    {"run": "snapshot", "q": "Which task is blocked? Give its id only.", "a": "T902", "grade": "exact"},
    {"run": "snapshot", "q": "Who owns task T901? Give the owner only.", "a": "kimi", "grade": "exact"},
    {
        "run": "cut",
        "q": "How many tasks does the ledger hold in total, including any not listed?",
        "a": 5,
        "grade": "number",
    },
    {
        "run": "snapshot",
        "q": "Can this projection check whether a seat is actually running (runtime attention)? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "brief",
        "q": "Does this brief carry any authority over identity? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {"run": "missing", "q": "Could the task ledger be read? Answer yes or no.", "a": "no", "grade": "exact"},
]
