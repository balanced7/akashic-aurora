"""AXI bench spec: `college` -- one course's source -> lecture -> audit -> teach-back record.

Courses live in files under AURORA_COLLEGE_ROOT (default: <repo>/artifacts/college). The bench
points that variable at a temporary directory outside the repo and builds the fixture here, at
import, through core.library.college itself: SEED cannot do it through the CLI, because seeding
runs once per side and a second `college start` of the same course is refused. The runs are
read paths (show) and a refused start, which writes nothing. College never calls a model.
"""

import os
import tempfile

_ROOT = tempfile.mkdtemp(prefix="axi-college-")
os.environ["AURORA_COLLEGE_ROOT"] = _ROOT  # inherited by every CLI run the harness makes

from core.library.college import run_college  # noqa: E402 -- reads the root set above

_LECTURE = "# Bus ordering\n\nThe bus orders messages by stream id, never by the sender's clock.\n"
run_college(
    "start",
    "bus-ordering",
    {"title": "How the bus orders messages", "topic": "stream ids", "lecturer": "claude", "auditor": "kimi"},
    actor="claude",
)
run_college(
    "source",
    "bus-ordering",
    {"source_id": "s1", "title": "bus.py", "locator": "core/comm/bus.py", "source_kind": "primary",
     "status": "verified", "receipt": "read lines 1-200", "retrieved_at": "2026-10-01T00:00:00Z"},
    actor="kimi",
)  # fmt: skip
run_college(
    "source",
    "bus-ordering",
    {"source_id": "s2", "title": "a blog post", "locator": "https://example.invalid/post",
     "source_kind": "secondary", "status": "candidate"},
    actor="claude",
)  # fmt: skip
run_college("lecture", "bus-ordering", {"text": _LECTURE}, actor="claude")
run_college(
    "audit",
    "bus-ordering",
    {"claim_id": "c1", "claim": "ordering is by stream id", "anchor": "orders messages by stream id",
     "species": "mechanism", "verdict": "supported", "receipt": "bus.py sorts by id", "source_ids": ["s1"]},
    actor="kimi",
)  # fmt: skip
run_college(
    "start",
    "fresh-course",
    {"title": "Wake seats", "topic": "per-session seats", "lecturer": "sol", "auditor": "deepseek"},
    actor="sol",
)

# The verb with its action and course: the conformance checks append a bogus flag to these, and
# without the positionals argparse reports them missing before it sees the flag.
VERB = "college show bus-ordering"
SEED: list = []
RUNS = {
    "show": ["college", "show", "bus-ordering"],
    "fresh": ["college", "show", "fresh-course"],
    "dup": [
        "college", "start", "bus-ordering", "--title", "x", "--topic", "y",
        "--lecturer", "a", "--auditor", "b", "--actor", "a",
    ],
}  # fmt: skip
EMPTY = None
QUESTIONS = [
    {"run": "show", "q": "Who is the designated auditor of the course?", "a": "kimi", "grade": "exact"},
    {"run": "show", "q": "How many source records does the course have?", "a": 2, "grade": "number"},
    {"run": "show", "q": "Is the lecture sealed? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "show", "q": "How many gaps does the course still have?", "a": 2, "grade": "number"},
    {"run": "fresh", "q": "Is the lecture of this course sealed? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "dup",
        "q": "Why was the start refused?",
        "a": "already exists",
        "grade": "contains",
    },
]
