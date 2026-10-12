"""AXI bench spec: `bifrost-sync` -- peek (and consume) the unread bus inbox."""

LONG = "Design notes for the cache layer: keep the write path synchronous. " * 40  # ~2.7k chars

VERB = "bifrost-sync"
SEED = [
    ["bifrost-send", "alice", "please review core/a.py before merge", "--to", "bench", "--kind", "request",
     "--expect-reply-within", "0"],
    ["bifrost-send", "bob", "FYI the build is green", "--to", "bench"],
    ["bifrost-send", "carol", "what port does redis use?", "--to", "bench", "--kind", "question",
     "--expect-reply-within", "0"],
    ["bifrost-send", "dave", LONG, "--to", "bench"],
]  # fmt: skip
RUNS = {
    "peek": ["bifrost-sync", "bench"],
    "consume": ["bifrost-sync", "bench", "--consume"],
    "none": ["bifrost-sync", "nobody"],
}
EMPTY = ["bifrost-sync", "nobody"]
QUESTIONS = [
    {"run": "peek", "q": "How many unread messages does bench have?", "a": 4, "grade": "number"},
    {"run": "peek", "q": "Which agent sent the request message?", "a": "alice", "grade": "exact"},
    {
        "run": "peek",
        "q": "How many of the unread messages are asks that need a reply (requests or questions)?",
        "a": 2,
        "grade": "number",
    },
    {
        "run": "peek",
        "q": "What exact command marks bench's unread messages as read (acknowledges them)? Give the command only.",
        "a": ["bifrost-sync", "bench", "--consume"],
        "grade": "contains",
    },
    {
        "run": "peek",
        "q": "What exact command shows the full body of dave's message? Give the command only.",
        "a": ["bifrost-fetch", "--get"],
        "grade": "contains",
    },
    {"run": "consume", "q": "How many messages were consumed?", "a": 4, "grade": "number"},
    {"run": "none", "q": "How many unread messages does nobody have?", "a": 0, "grade": "number"},
]
