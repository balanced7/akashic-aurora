"""AXI bench spec: `tally` -- the blind-counter consensus matrix for one opening.

tally reads files, not the store, so the fixture is written here, at import, into a temporary
directory outside the repo: an opening with four questions, three counters that name it, and a
brief that names it without verdicts. Both trees read the same absolute paths.
"""

import tempfile
from pathlib import Path

_DIR = Path(tempfile.mkdtemp(prefix="axi-tally-"))
_RESEARCH = _DIR / "research"
_EMPTY = _DIR / "empty"
_RESEARCH.mkdir()
_EMPTY.mkdir()
OPENING = _RESEARCH / "seat-routing-opening-2026-10.md"
OPENING.write_text(
    "# Seat routing opening\n\nQ1: keep the per-session wake seat?\nQ2: move routing into the bus?\n"
    "Q3: retire the HMAC bridge?\nQ4: is the cost model sound?\n",
    encoding="utf-8",
)
for author, verdicts in {
    "kimi": {"Q1": "KEEP", "Q2": "AMEND", "Q3": "KILL", "Q4": "YES"},
    "deepseek": {"Q1": "KEEP", "Q2": "KILL", "Q3": "KILL"},
    "claude": {"Q1": "KEEP", "Q2": "AMEND", "Q3": "KILL", "Q4": "YES"},
}.items():
    body = "\n".join(f"{q}: {v} -- reasons in the appendix" for q, v in verdicts.items())
    (_RESEARCH / f"{author}-seat-routing-counter.md").write_text(
        f"# Counter to seat-routing-opening-2026-10\n\n{body}\n", encoding="utf-8"
    )
(_RESEARCH / "sol-brief.md").write_text(
    "Brief: read seat-routing-opening-2026-10 before the fence.\n", encoding="utf-8"
)
LONELY = _EMPTY / "lonely-opening-2026-10.md"
LONELY.write_text("Q1: anyone?\n", encoding="utf-8")

# Two words: the conformance checks append a bogus flag to the first run's first two arguments
# (the verb and its required opening); without the positional argparse reports it missing first.
VERB = "tally <opening>"
SEED: list = []
RUNS = {
    "matrix": ["tally", str(OPENING), "--research-dir", str(_RESEARCH)],
    "none": ["tally", str(LONELY), "--research-dir", str(_EMPTY)],
}
EMPTY = ["tally", str(LONELY), "--research-dir", str(_EMPTY)]
QUESTIONS = [
    {"run": "matrix", "q": "How many questions do all counters agree on?", "a": 2, "grade": "number"},
    {
        "run": "matrix",
        "q": "Which question ids are in conflict? List them separated by commas.",
        "a": ["Q2"],
        "grade": "set",
    },
    {"run": "matrix", "q": "What verdict did deepseek give on Q2?", "a": "KILL", "grade": "exact"},
    {"run": "matrix", "q": "How many counters were found?", "a": 3, "grade": "number"},
    {
        "run": "matrix",
        "q": "Which file names the opening but is not a counter? Give the file name only.",
        "a": "sol-brief.md",
        "grade": "contains",
    },
    {"run": "none", "q": "How many counters were found for this opening?", "a": 0, "grade": "number"},
]
