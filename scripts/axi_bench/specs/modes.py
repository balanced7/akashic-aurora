"""AXI bench spec: `modes` -- interpretive vs precompiled memory, offline paths only.

`modes compare` runs four replay arms with real models, so it only runs here without the flags
it requires, which it refuses first. `show` reads the environment (the bench sets no
AKASHIC_MEMORY_MODE, so the default applies), `placement` judges the seeded lessons, and
`stale` reads the recompile queue (empty: no lesson here was ever compiled)."""

VERB = "modes"
SEED = [
    ["learn", "bench", "--experiment", "no_force_push", "--tried", "a", "--result", "b",
     "--recommend", "Never run `git push --force` on a shared branch."],
    ["learn", "bench", "--experiment", "short_titles", "--tried", "a", "--result", "b",
     "--recommend", "Keep commit titles under 72 characters."],
]  # fmt: skip
RUNS = {
    "show": ["modes", "show"],
    "placement": ["modes", "placement"],
    "stale": ["modes", "stale"],
    "compare": ["modes", "compare", "--base", "baseline"],
}
EMPTY = ["modes", "stale"]
QUESTIONS = [
    {"run": "show", "q": "Which memory mode is active?", "a": "interpretive", "grade": "exact"},
    {
        "run": "show",
        "q": "Which environment variable sets the memory mode? Give the name only.",
        "a": "AKASHIC_MEMORY_MODE",
        "grade": "exact",
    },
    {"run": "placement", "q": "What move is planned for the lesson short_titles?", "a": "keep", "grade": "exact"},
    {"run": "stale", "q": "How many compiled lessons are stale?", "a": 0, "grade": "number"},
    {
        "run": "compare",
        "q": "Which flags are missing from this modes compare command? List them separated by commas.",
        "a": ["--compiled", "--scenario"],
        "grade": "set",
    },
]
