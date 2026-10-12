"""AXI bench spec: `knowledge-map` -- walk a topic's lesson/note/doc neighborhood.

The topic is a made-up word (quokkadb) seeded into the sandbox store, so the docs layer, which
reads the checkout's docs/library, contributes nothing on either side of the bench.
"""

VERB = "knowledge-map"
SEED = [
    ["note", "alice", "--title", "Chose quokkadb for the embedded store",
     "--note", "We picked quokkadb over leveldb because it ships with python and survives crashes"],
    ["note", "bob", "--title", "Old cache design", "--note", "The quokkadb cache layer was dropped in favour of redis"],
    ["note", "bob", "--retire", "Old cache design"],
    ["learn", "alice", "--experiment", "quokka_wal_mode", "--tried", "ran quokkadb without WAL",
     "--result", "writers blocked readers", "--recommend", "Use when quokkadb locks under load: enable WAL mode",
     "--category", "performance"],
    ["learn", "bob", "--experiment", "quokka_backup", "--tried", "copied the quokkadb file while open",
     "--result", "corrupt backup", "--recommend", "Use the quokkadb online backup command, never a file copy",
     "--category", "data"],
]  # fmt: skip
RUNS = {
    "topic": ["knowledge-map", "quokkadb"],
    "none": ["knowledge-map", "zebraunicorn"],
}
EMPTY = ["knowledge-map", "anything"]
QUESTIONS = [
    {"run": "topic", "q": "How many nodes are in the surface layer?", "a": 3, "grade": "number"},
    {"run": "topic", "q": "How many nodes are in the archive layer?", "a": 1, "grade": "number"},
    {
        "run": "topic",
        "q": "Which archived record is on this topic? Give its title only.",
        "a": "Old cache design",
        "grade": "exact",
    },
    {
        "run": "topic",
        "q": "What exact command shows the full record of the quokka_backup lesson? Give the command only.",
        "a": ["recall", "--full", "learn:experiment:quokka_backup"],
        "grade": "contains",
    },
    {"run": "none", "q": "How many nodes did the walk find in total?", "a": 0, "grade": "number"},
]
