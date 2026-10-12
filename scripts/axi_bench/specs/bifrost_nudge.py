"""AXI bench spec: `bifrost-nudge` -- a targeted interrupt, steer or inform to one peer."""

VERB = "bifrost-nudge"
SEED = []
RUNS = {
    "interrupt": ["bifrost-nudge", "claude", "look at the failing test", "--to", "deepseek"],
    "steer": ["bifrost-nudge", "claude", "prefer the small fix", "--to", "deepseek", "--mode", "steer"],
    "bad_mode": ["bifrost-nudge", "claude", "x", "--to", "deepseek", "--mode", "yell"],
    "no_to": ["bifrost-nudge", "claude", "x"],
}
EMPTY = None
QUESTIONS = [
    {"run": "interrupt", "q": "Which agent was nudged?", "a": "deepseek", "grade": "exact"},
    {"run": "interrupt", "q": "Which nudge mode was used?", "a": "interrupt", "grade": "exact"},
    {
        "run": "steer",
        "q": "Will the nudged agent drop the task it is working on? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "bad_mode",
        "q": "Which modes are valid? List them separated by commas.",
        "a": ["interrupt", "steer", "inform"],
        "grade": "set",
    },
    {"run": "no_to", "q": "Was the nudge sent? Answer yes or no.", "a": "no", "grade": "exact"},
]
