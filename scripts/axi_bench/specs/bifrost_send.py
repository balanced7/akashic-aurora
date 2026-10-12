"""AXI bench spec: `bifrost-send` -- send one message on the bus, with its delivery verdict."""

VERB = "bifrost-send"
SEED = []
ASK = ["bifrost-send", "deepseek", "please review core/a.py", "--to", "claude", "--kind", "request"]
RUNS = {
    "ask": ASK,
    "again": ASK,  # the identical ask while the first is pending: collapsed, not re-sent
    "broadcast": ["bifrost-send", "deepseek", "standup in five minutes", "--broadcast"],
    "no_to": ["bifrost-send", "deepseek", "hello"],
}
EMPTY = None
QUESTIONS = [
    {"run": "ask", "q": "What kind was the message sent as?", "a": "request", "grade": "exact"},
    {
        "run": "ask",
        "q": "Within how many seconds is a reply expected? Answer 0 if no reply deadline was set.",
        "a": 1800,
        "grade": "number",
    },
    {"run": "again", "q": "Was the message actually sent this time? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "again",
        "q": "Which command does the output suggest using instead of sending again? Give the command name only.",
        "a": ["nudge"],
        "grade": "contains",
    },
    {
        "run": "broadcast",
        "q": "Was this message sent to one agent or to every agent? Answer one or every.",
        "a": "every",
        "grade": "exact",
    },
    {"run": "no_to", "q": "Which flag is missing? Give the flag only.", "a": "--to", "grade": "exact"},
]
