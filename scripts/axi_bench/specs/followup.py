"""AXI bench spec: `followup` -- ask a question back on a verdict file and defer it to a seat.

followup appends to a verdict file inside the checkout and files a defer item in the checkout's
queue (state/coord/defer_queue.json), so the runs write only to the measured tree: the bench
questions a tracked report that has an Open Questions block and no Q-ids yet, so the first
question is Q1 in both trees.
"""

VERDICT = "docs/library/report/20260718_charter-framework-draft-deepseek-2026-07_7c6022.md"
VERB = "followup"
SEED = []
RUNS = {
    "ask": ["followup", "bench", "--on", VERDICT, "--to", "kimi", "--ask", "does the charter still need a quorum?"],
    "again": ["followup", "bench", "--on", VERDICT, "--to", "kimi", "--ask", "does the charter still need a quorum?"],
    "missing": ["followup", "bench", "--on", "docs/no-such-verdict.md", "--to", "kimi", "--ask", "x"],
    "outside": ["followup", "bench", "--on", "/etc/hosts", "--to", "kimi", "--ask", "x"],
}
EMPTY = None
QUESTIONS = [
    {"run": "ask", "q": "What question id was assigned?", "a": "Q1", "grade": "exact"},
    {"run": "ask", "q": "Which seat is responsible for answering?", "a": "kimi", "grade": "exact"},
    {"run": "ask", "q": "What exact command would show the item deferred to that seat? Give the command only.",
     "a": ["defer kimi --list"], "grade": "contains"},
    {"run": "again", "q": "Was a new question added to the file this time? Answer yes or no.", "a": "no",
     "grade": "exact"},
    {"run": "missing", "q": "Does the verdict file exist? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "outside", "q": "Was the question filed? Answer yes or no.", "a": "no", "grade": "exact"},
]  # fmt: skip
