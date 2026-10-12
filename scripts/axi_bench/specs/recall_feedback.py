"""AXI bench spec: `recall-feedback` -- vote a recalled lesson useful or noise.

The runs share one store and run in order, so the second useful vote (in a second domain) is the
one that makes the lesson domain-general.
"""

VERB = "recall-feedback"
SEED = [
    ["learn", "alice", "--experiment", "tonemap_order", "--tried", "a", "--result", "b",
     "--recommend", "Use when adding a tonemap: put it after the highlight pass.", "--category", "vfx"],
    ["learn", "alice", "--experiment", "noisy_one", "--tried", "a", "--result", "b",
     "--recommend", "Use when anything happens: do something.", "--category", "misc"],
]  # fmt: skip
SRC = "learn:experiment:tonemap_order"
RUNS = {
    "vfx": ["recall-feedback", "--source", SRC, "--useful", "--domain", "vfx"],
    "system": ["recall-feedback", "--source", SRC, "--useful", "--domain", "system"],
    "noise": ["recall-feedback", "--source", "learn:experiment:noisy_one", "--noise"],
}
EMPTY = None
QUESTIONS = [
    {"run": "vfx", "q": "Was the vote recorded? Answer yes or no.", "a": "yes", "grade": "exact"},
    {"run": "vfx", "q": "In which domain was the lesson credited?", "a": "vfx", "grade": "exact"},
    {
        "run": "system",
        "q": "Will this lesson now surface in every domain? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
    {"run": "system", "q": "How many useful votes does this lesson have now?", "a": 2, "grade": "number"},
    {"run": "noise", "q": "What kind of vote was recorded: useful or noise?", "a": "noise", "grade": "exact"},
]
