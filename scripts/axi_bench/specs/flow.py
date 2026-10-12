"""AXI bench spec: `flow` -- the waterfall of recent message flows across lanes.

A reply links to its ask by stream id, which the seed cannot know in advance, so every seeded
message is its own flow; the bench measures counts, routes, kinds and the cut list.
"""

VERB = "flow"
SEED = [
    ["bifrost-send", "alice", "please review core/a.py", "--to", "bob", "--kind", "request",
     "--expect-reply-within", "0"],
    ["bifrost-send", "bob", "the build is green on main", "--to", "alice"],
    ["bifrost-send", "carol", "handing off the parser work", "--to", "dave", "--kind", "handoff",
     "--expect-reply-within", "0"],
    ["bifrost-send", "erin", "status: idle", "--to", "alice"],
]  # fmt: skip
RUNS = {"all": ["flow"], "alice": ["flow", "alice"], "cut": ["flow", "--limit", "2"]}
EMPTY = ["flow"]
QUESTIONS = [
    {"run": "all", "q": "How many flows are in the window?", "a": 4, "grade": "number"},
    {"run": "all", "q": "Who did carol send the handoff to?", "a": "dave", "grade": "exact"},
    {"run": "alice", "q": "How many flows touch alice?", "a": 3, "grade": "number"},
    {"run": "cut", "q": "How many flows does this output show?", "a": 2, "grade": "number"},
    {"run": "cut", "q": "What exact command would show every flow? Give the command only.",
     "a": ["flow", "--limit"], "grade": "contains"},
]  # fmt: skip
