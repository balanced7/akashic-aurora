"""AXI bench spec: `bifrost-skip-to-now` -- advance one agent's consume cursors to the tails.

The verb refuses unless the fleet is paused, so the runs go skip (paused by the seed), resume,
then skip again (refused). The resume run's output is counted in the character totals.
"""

VERB = "bifrost-skip-to-now"
SKIP = ["bifrost-skip-to-now", "deepseek", "--by", "claude", "--reason", "echo storm"]
SEED = [
    ["bifrost-send", "claude", "first", "--to", "deepseek"],
    ["bifrost-send", "claude", "second", "--to", "deepseek"],
    ["bifrost-pause", "--reason", "skip ceremony", "--ttl", "600"],
]
RUNS = {"skip": SKIP, "resume": ["bifrost-resume"], "refused": SKIP}
EMPTY = None
QUESTIONS = [
    {"run": "skip", "q": "Whose cursors were advanced?", "a": "deepseek", "grade": "exact"},
    {"run": "skip", "q": "Who authorized the skip?", "a": "claude", "grade": "exact"},
    {"run": "skip", "q": "Was an audit record written? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "refused", "q": "Did the skip happen? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "refused",
        "q": "What command must be run before the skip can succeed? Give the command only.",
        "a": ["bifrost-pause"],
        "grade": "contains",
    },
]
