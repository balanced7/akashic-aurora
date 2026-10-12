"""AXI bench spec: `tool` -- list and run play-tier draft tools (data/play/<agent>/).

Play tools live in the checkout, so the bench reads the ones git tracks (claude's campfire and
verbthread, kimi's premonition), the same in both trees. The one run uses a timeout far below
Python's start-up time: the sandbox kills the tool before it does anything and writes a CRASH
receipt into the measured tree's data/play/kimi/runs/, so no draft tool's code really runs.
"""

VERB = "tool"
SEED = []
RUNS = {
    "list": ["tool", "list"],
    "list_kimi": ["tool", "list", "kimi"],
    "timeout": ["tool", "run", "kimi/premonition", "--timeout", "0.001"],
    "missing": ["tool", "run", "kimi/ghost"],
}
EMPTY = ["tool", "list", "nobody"]
QUESTIONS = [
    {"run": "list", "q": "Which agents have play tools? List them separated by commas.", "a": ["claude", "kimi"],
     "grade": "set"},
    {"run": "list", "q": "How many play tools are there in total?", "a": 3, "grade": "number"},
    {"run": "list", "q": "How many receipts does the verbthread tool have?", "a": 4, "grade": "number"},
    {"run": "timeout", "q": "Did the tool run succeed? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "missing", "q": "Does kimi have a play tool named ghost? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "list_kimi", "q": "What exact command runs kimi's premonition tool? Give the command only.",
     "a": ["tool run kimi/premonition"], "grade": "contains"},
]  # fmt: skip
