"""AXI bench spec: `bifrost-ack` -- record that you handled a salient bus message.

Only the refusal paths are benched: an ackable message's stream id is minted at send time, and a
spec's argv is fixed before the seed runs, so the success path is pinned in tests instead.
"""

VERB = "bifrost-ack"
SEED = []
RUNS = {
    "not_promoted": ["bifrost-ack", "claude", "1-0"],
    "quarantined": ["bifrost-ack", "alice", "1-0"],
    "sha": ["bifrost-ack", "claude", "abcdef12"],
}
EMPTY = None
QUESTIONS = [
    {"run": "not_promoted", "q": "Was the ack recorded? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "not_promoted",
        "q": "Which kinds of messages can carry acks? List them separated by commas.",
        "a": ["handoff", "decision", "completion", "blocker"],
        "grade": "set",
    },
    {"run": "not_promoted", "q": "Which message id was the ack for?", "a": ["1-0"], "grade": "contains"},
    {
        "run": "quarantined",
        "q": "What trust status does the acking agent have? Answer with one word.",
        "a": "quarantined",
        "grade": "exact",
    },
    {
        "run": "sha",
        "q": "Which command does the output point to for finding the message's full stream id? "
        "Give the command name only.",
        "a": ["promoted"],
        "grade": "contains",
    },
]
