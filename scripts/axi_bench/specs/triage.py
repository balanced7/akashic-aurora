"""AXI bench spec: `triage` -- lessons ranked by measured value, for a human to adjudicate.

Impressions come only from the harness hooks, so nothing here reaches cost-without-return; the
seeded signal is votes: two useful votes make a protected lesson, a noise vote a noise-voted one,
and a vote on a lesson that does not exist a ghost.
"""

VERB = "triage"
SEED = [
    ["learn", "alice", "--experiment", "proven_core", "--tried", "a", "--result", "b", "--recommend", "Use when x: y."],
    ["learn", "alice", "--experiment", "off_target", "--tried", "a", "--result", "b", "--recommend", "Use when z: w."],
    ["learn", "alice", "--experiment", "never_seen", "--tried", "a", "--result", "b", "--recommend", "Use when q: r."],
    ["recall-feedback", "--source", "learn:experiment:proven_core", "--useful"],
    ["recall-feedback", "--source", "learn:experiment:proven_core", "--useful"],
    ["recall-feedback", "--source", "learn:experiment:off_target", "--noise"],
    ["recall-feedback", "--source", "learn:experiment:renamed_away", "--useful"],
]
RUNS = {"report": ["triage"]}
EMPTY = ["triage"]
QUESTIONS = [
    {"run": "report", "q": "How many lessons are in the corpus?", "a": 3, "grade": "number"},
    {"run": "report", "q": "Which lesson is in the protected core?", "a": "learn:experiment:proven_core",
     "grade": "contains"},
    {"run": "report", "q": "How many useful votes does proven_core have?", "a": 2, "grade": "number"},
    {"run": "report", "q": "Which lesson was voted noise? Give its name.", "a": "off_target", "grade": "contains"},
    {"run": "report", "q": "How many ghost counters are there?", "a": 1, "grade": "number"},
    {"run": "report", "q": "Does this report prune anything by itself? Answer yes or no.", "a": "no", "grade": "exact"},
]  # fmt: skip
