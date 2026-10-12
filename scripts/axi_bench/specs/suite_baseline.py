"""AXI bench spec: `suite-baseline` -- the test-suite receipt the next seat diffs.

READ PATHS ONLY. The baseline is a file inside the repo (state/coord/suite_baseline.json,
committed) and recording one overwrites it with no way to point it elsewhere; `--whose` runs the
whole test suite. So the bench reads the committed baseline (identical in both trees) with
`--show`, diffs a small pytest output written here into a temporary directory with `--check`,
and checks the usage error when no --from-file is given. Nothing is recorded.
"""

import tempfile
from pathlib import Path

_DIR = Path(tempfile.mkdtemp(prefix="axi-suite-"))
PYTEST_OUT = _DIR / "pytest.txt"
PYTEST_OUT.write_text(
    "============ short test summary info ============\n"
    "FAILED tests/test_agent_interface.py::test_redis_down_file_fallback - AssertionError\n"
    "FAILED tests/test_atoms_v11.py::test_lineage_resolve_current_and_lineage_backlinks - KeyError\n"
    "FAILED tests/test_parser_roundtrip.py::test_new_flag_survives - AssertionError\n"
    "3 failed, 900 passed in 61.2s\n",
    encoding="utf-8",
)

# Two words: the conformance checks append a bogus flag to the verb and its required seat id;
# without the positional argparse reports it missing before it sees the flag.
VERB = "suite-baseline bench"
SEED: list = []
RUNS = {
    "show": ["suite-baseline", "bench", "--show"],
    "check": ["suite-baseline", "bench", "--check", "--from-file", str(PYTEST_OUT)],
    "no_file": ["suite-baseline", "bench"],
}
EMPTY = None
QUESTIONS = [
    {"run": "show", "q": "How many known failures does the recorded baseline hold?", "a": 100, "grade": "number"},
    {"run": "show", "q": "At which commit sha was the baseline recorded?", "a": "5ba81ba", "grade": "contains"},
    {"run": "check", "q": "How many NEW failures does this run have against the baseline?", "a": 1, "grade": "number"},
    {
        "run": "check",
        "q": "Which test is the new failure? Give its node id.",
        "a": "test_parser_roundtrip.py::test_new_flag_survives",
        "grade": "contains",
    },
    {"run": "check", "q": "How many of this run's failures were already in the baseline?", "a": 2, "grade": "number"},
    {
        "run": "no_file",
        "q": "Which flag must be given to record or check a baseline? Give the flag only.",
        "a": "--from-file",
        "grade": "contains",
    },
]
