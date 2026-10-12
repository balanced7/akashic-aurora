"""AXI bench spec: `reply` -- answer the operator, with an honest delivery verdict."""

VERB = "reply"
SEED = []
RUNS = {
    "sent": ["reply", "the parser fix is in"],
    "empty": ["reply"],
    "unreadable": ["reply", "--text-file", "/nonexistent/reply.txt"],
}
EMPTY = None
QUESTIONS = [
    {"run": "sent", "q": "Did the bus accept the reply? Answer yes or no.", "a": "yes", "grade": "exact"},
    {
        "run": "sent",
        "q": "Does the output confirm that the operator has read the reply? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {"run": "sent", "q": "Who is the reply addressed to?", "a": "daniil", "grade": "exact"},
    {"run": "empty", "q": "Was the reply sent? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "empty", "q": "Why was nothing sent? Answer in one word.", "a": ["empty"], "grade": "contains"},
    {
        "run": "unreadable",
        "q": "Which file could not be read? Give the path only.",
        "a": "/nonexistent/reply.txt",
        "grade": "exact",
    },
]
