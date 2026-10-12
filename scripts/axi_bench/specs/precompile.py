"""AXI bench spec: `precompile` -- lessons into harness primitives, offline paths.

No path here calls a model. `build` without --force compiles only lessons that pass the gates;
freshly recorded lessons are not yet stable, so it builds nothing and says so. `check` reads the
checkout's own generated pieces for drift and writes nothing."""

VERB = "precompile"
SEED = [
    ["learn", "bench", "--experiment", "no_force_push", "--tried", "a", "--result", "b",
     "--recommend", "Never run `git push --force` on a shared branch."],
    ["learn", "bench", "--experiment", "short_titles", "--tried", "a", "--result", "b",
     "--recommend", "Keep commit titles under 72 characters."],
]  # fmt: skip
RUNS = {
    "plan": ["precompile", "plan"],
    "build": ["precompile", "build"],
    "check": ["precompile", "check"],
}
EMPTY = ["precompile", "plan"]
QUESTIONS = [
    {"run": "plan", "q": "How many lessons are in the precompile plan?", "a": 2, "grade": "number"},
    {"run": "plan", "q": "How many lessons pass every compile gate?", "a": 0, "grade": "number"},
    {
        "run": "plan",
        "q": "Which gates is short_titles still failing? List the gate names separated by commas.",
        "a": ["proven", "stable"],
        "grade": "set",
    },
    {"run": "build", "q": "Was a precompiled candidate built? Answer yes or no.", "a": "no", "grade": "exact"},
]
