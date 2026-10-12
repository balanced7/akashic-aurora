"""AXI bench spec: `defer` -- the shared queue of commands waiting for a capable seat.

The queue lives in the checkout (state/coord/defer_queue.json, tracked), so the bench reads the
same 20 pending items in both trees and the runs that file and discharge write only to the
measured tree's copy. The sandbox has no fleet roster, so the seat cannot be confirmed.
"""

VERB = "defer"
SEED = []
RUNS = {
    "list": ["defer", "bench", "--list"],
    "file": ["defer", "bench", "rerun the full suite", "--needs", "exec", "--why", "baseline"],
    "done": ["defer", "bench", "--done", "fd3e244095", "--receipt", "fixed in abc123"],
    "done_missing": ["defer", "bench", "--done", "nope", "--receipt", "x"],
}
EMPTY = None
QUESTIONS = [
    {"run": "list", "q": "How many commands are pending?", "a": 20, "grade": "number"},
    {"run": "list", "q": "What capability does item c7f905eddc need?", "a": "exec", "grade": "exact"},
    {"run": "list", "q": "Is bench confirmed as a real seat in the fleet roster? Answer yes or no.", "a": "no",
     "grade": "exact"},
    {"run": "list", "q": "What command discharges a pending item? Give the command only.",
     "a": ["defer bench --done", "--receipt"], "grade": "contains"},
    {"run": "file", "q": "What capability does the filed command wait for?", "a": "exec", "grade": "exact"},
    {"run": "done_missing", "q": "Was the item discharged? Answer yes or no.", "a": "no", "grade": "exact"},
]  # fmt: skip
