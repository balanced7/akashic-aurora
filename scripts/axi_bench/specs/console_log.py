"""AXI bench spec: `console-log` -- durable console events (interjections, pause/resume, file drops).

The console writes these from the live cockpit; the seed writes the same records through
`events --capture`, the CLI door to the same event log.
"""

import json

VERB = "console-log"
SEED = [
    ["events", "--capture", "--kind", "interjection", "--agent", "user",
     "--summary", "user [steer] -> claude: also cover the null case",
     "--detail-json", json.dumps({"text": "also cover the null case", "to": "claude", "intent": "steer"})],
    ["events", "--capture", "--kind", "bus_control", "--agent", "user", "--summary", "user pause the collaboration",
     "--detail-json", json.dumps({"action": "pause", "reason": "reviewing the auth change", "by": "user"})],
    ["events", "--capture", "--kind", "file_drop", "--agent", "user", "--summary", "user shared file docs/spec.md",
     "--refs", "file:docs/spec.md", "--detail-json", json.dumps({"path": "docs/spec.md", "bytes": 2048, "by": "user"})],
    ["events", "--capture", "--kind", "bus_control", "--agent", "user", "--summary", "user resume the collaboration",
     "--detail-json", json.dumps({"action": "resume", "reason": "", "by": "user"})],
]  # fmt: skip
RUNS = {"all": ["console-log"], "page": ["console-log", "--limit", "2"]}
EMPTY = ["console-log"]
QUESTIONS = [
    {"run": "all", "q": "How many console events are listed?", "a": 4, "grade": "number"},
    {"run": "all", "q": "Which agent was the interjection addressed to?", "a": "claude", "grade": "exact"},
    {"run": "all", "q": "Why was the collaboration paused?", "a": ["auth"], "grade": "contains"},
    {"run": "all", "q": "How many bytes was the shared file docs/spec.md?", "a": 2048, "grade": "number"},
    {"run": "page", "q": "Does this output show every console event there is? Answer yes or no.", "a": "no",
     "grade": "exact"},
]  # fmt: skip
