"""AXI bench spec: `clobber-scan` -- unguarded writes to shared control keys in one file.

The verb scans a file, not the store, so the fixtures are written here, at import, into a
temporary directory outside the repo: a module with three unguarded control-key writes (and
two guarded ones that must not flag), and a clean module. Both trees read the same paths.
"""

import tempfile
from pathlib import Path

_DIR = Path(tempfile.mkdtemp(prefix="axi-clobber-"))
CEREMONY = _DIR / "ceremony.py"
CEREMONY.write_text(
    """from core.comm import control


def pause_fleet(c):
    c.set(_pause_key(), "1")


def guarded_resume(c):
    if was_paused():
        control.resume()


def reset_lane(c, lane):
    c.delete(_cursor_key(lane))
    c.set(_drain_key(lane), "1")


def safe_drain(c, lane):
    if drain_requested(lane):
        c.delete(_drain_key(lane))
""",
    encoding="utf-8",
)
CLEAN = _DIR / "clean.py"
CLEAN.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

# Two words: the conformance checks append a bogus flag to the verb and its required path;
# without the positional argparse reports it missing before it sees the flag.
VERB = "clobber-scan <path>"
SEED: list = []
RUNS = {"ceremony": ["clobber-scan", str(CEREMONY)], "clean": ["clobber-scan", str(CLEAN)]}
EMPTY = ["clobber-scan", str(CLEAN)]
QUESTIONS = [
    {"run": "ceremony", "q": "How many unguarded control-key writes were found?", "a": 3, "grade": "number"},
    {
        "run": "ceremony",
        "q": "On which line numbers are the unguarded writes? List them separated by commas.",
        "a": ["5", "14", "15"],
        "grade": "set",
    },
    {"run": "ceremony", "q": "Which control family does the write on line 14 touch?", "a": "cursor", "grade": "exact"},
    {
        "run": "ceremony",
        "q": "Is the control.resume() call on line 10 flagged? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {"run": "clean", "q": "How many unguarded control-key writes were found?", "a": 0, "grade": "number"},
]
