"""AXI bench spec: `watch` -- declare, check and close the out-of-band deadman's expectation.

The expectation is a file in the checkout (state/expect/run-active.json, or
$AKASHIC_RUN_EXPECTATION), so the runs write only to the measured tree. Nothing here starts a
watcher: the scheduled failsafe_watcher reads the real checkout's file, never the bench tree's,
and a declaration with --grace 0 is how the status run sees an alarm without waiting.
"""

VERB = "watch"
SEED = []
RUNS = {
    "none": ["watch", "bench", "--status"],
    "declare": ["watch", "bench", "--declare", "nightly reindex", "--grace", "600"],
    "open": ["watch", "bench", "--status"],
    "stand_down": ["watch", "bench", "--stand-down"],
    "down": ["watch", "bench", "--status"],
    "declare_tight": ["watch", "bench", "--declare", "schema migration", "--grace", "0"],
    "alarm": ["watch", "bench", "--status"],
}
EMPTY = ["watch", "bench", "--status"]
QUESTIONS = [
    {"run": "none", "q": "Is any run expectation open? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "declare", "q": "How many minutes of silence are allowed before it alarms?", "a": 10, "grade": "number"},
    {"run": "declare", "q": "What exact command tells the watcher the run is still alive? Give the command only.",
     "a": ["watch bench --checkpoint"], "grade": "contains"},
    {"run": "open", "q": "Which run is declared?", "a": ["nightly reindex"], "grade": "contains"},
    {"run": "down", "q": "Is the watcher expecting activity right now? Answer yes or no.", "a": "no",
     "grade": "exact"},
    {"run": "alarm", "q": "Would the watcher alarm right now? Answer yes or no.", "a": "yes", "grade": "exact"},
]  # fmt: skip
