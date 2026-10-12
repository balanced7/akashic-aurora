"""AXI bench spec: `bifrost-resume` -- un-freeze the bus auto-responders."""

VERB = "bifrost-resume"
SEED = [["bifrost-pause", "--reason", "operator barge-in", "--ttl", "600"]]
RUNS = {
    "resume": ["bifrost-resume"],
    "again": ["bifrost-resume"],  # nothing left to resume
}
EMPTY = ["bifrost-resume"]
QUESTIONS = [
    {"run": "resume", "q": "Did the resume succeed? Answer yes or no.", "a": "yes", "grade": "exact"},
    {
        "run": "resume",
        "q": "Was the bus paused before this command ran? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
    {
        "run": "again",
        "q": "Was the bus paused before this command ran? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "resume",
        "q": "Can the auto-responders take new work now? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
]
