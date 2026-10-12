"""AXI bench spec: `scope` -- where lessons apply: the tree, one lesson, widening proposals."""

VERB = "scope"
SEED = [
    *[
        ["learn", "bench", "--experiment", f"uni_{i}", "--tried", "a", "--result", "b", "--scope", "universal"]
        for i in (1, 2, 3)
    ],
    ["learn", "bench", "--experiment", "codex_only", "--tried", "a", "--result", "b", "--scope", "harness:codex-cli"],
    ["learn", "bench", "--experiment", "gpt_on_codex", "--tried", "a", "--result", "b",
     "--scope", "harness:codex-cli model:gpt"],
]  # fmt: skip
RUNS = {
    "tree": ["scope", "tree"],
    "show": ["scope", "show", "--experiment", "gpt_on_codex"],
    "proposals": ["scope", "proposals"],
    "missing": ["scope", "show", "--experiment", "no_such_lesson"],
}
EMPTY = ["scope", "tree"]
QUESTIONS = [
    {"run": "tree", "q": "How many lessons are there in total, across all scopes?", "a": 5, "grade": "number"},
    {"run": "tree", "q": "How many lessons apply universally?", "a": 3, "grade": "number"},
    {"run": "tree", "q": "Which lesson is scoped to harness:codex-cli alone?", "a": "codex_only", "grade": "exact"},
    {
        "run": "show",
        "q": "What is the scope of the lesson gpt_on_codex?",
        "a": ["harness:codex-cli", "model:gpt"],
        "grade": "contains",
    },
    {"run": "proposals", "q": "How many scope widening proposals are there?", "a": 0, "grade": "number"},
    {"run": "missing", "q": "Does a lesson named no_such_lesson exist? Answer yes or no.", "a": "no", "grade": "exact"},
]
