"""AXI bench spec: `story` -- the narrative atlas, a track's chapters, themes."""

VERB = "story"
SEED = [
    ["log", "commit", "--summary", "fixed the port clash in the test runner", "--source", "alice:commit",
     "--category", "testing"],
    ["log", "decision", "--summary", "chose sqlite for the embedded store", "--source", "bob:decision",
     "--category", "architecture"],
    ["log", "note", "--summary", "benchmarked recall latency at 40ms", "--source", "alice:note",
     "--category", "performance"],
    ["learn", "alice", "--experiment", "port_fix", "--tried", "a", "--result", "b", "--recommend", "check port",
     "--category", "testing"],
    ["story", "--mark", "Storage sprint"],
]  # fmt: skip
RUNS = {
    "atlas": ["story"],
    "track": ["story", "--track", "ai-setup"],
    "themes": ["story", "--themes"],
    "none": ["story", "--theme", "nope"],
}
EMPTY = ["story"]
QUESTIONS = [
    {"run": "atlas", "q": "How many chapters does the ai-setup track have?", "a": 2, "grade": "number"},
    {
        "run": "track",
        "q": "What is the title of the chapter that has exactly one beat?",
        "a": "Storage sprint",
        "grade": "exact",
    },
    {"run": "track", "q": "How many beats does the chapter titled 'check port' have?", "a": 4, "grade": "number"},
    {"run": "themes", "q": "How many beats carry the memory theme?", "a": 2, "grade": "number"},
    {"run": "none", "q": "How many chapters contain the theme 'nope'?", "a": 0, "grade": "number"},
    {
        "run": "track",
        "q": "What exact command would show the full detail of the chapter titled 'Storage sprint'? "
        "Give the command only.",
        "a": ["story", "--chapter", "chapter_"],
        "grade": "contains",
    },
]
