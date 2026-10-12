"""AXI bench spec: `fleet` -- the local-model roster (static data in core/fleet/models.json).

Offline paths only: the roster, a filtered roster, select (pure ranking over the roster) and the
`call` usage error. `--probe` (asks Ollama) and a real `call` (runs a model) are not benched.
"""

VERB = "fleet"
SEED = []
RUNS = {
    "list": ["fleet"],
    "select": ["fleet", "select", "--capability", "generalist"],
    "nofit": ["fleet", "select", "--capability", "extract"],
    "callerr": ["fleet", "call"],
}
EMPTY = ["fleet", "--status", "retired"]
QUESTIONS = [
    {"run": "list", "q": "How many models are in the roster?", "a": 8, "grade": "number"},
    {
        "run": "list",
        "q": "Which models have the status gated? Give the model names, separated by commas.",
        "a": ["gpt-oss:20b", "qwen3-coder:30b"],
        "grade": "set",
    },
    {"run": "list", "q": "What is the context window, in tokens, of glm-4.7-flash?", "a": 64000, "grade": "number"},
    {"run": "list", "q": "How many GB of VRAM does qwen3.5:4b need?", "a": 4, "grade": "number"},
    {"run": "select", "q": "Which model tag was selected?", "a": "glm-4.7-flash", "grade": "exact"},
    {"run": "nofit", "q": "Did any model fit the request? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "callerr",
        "q": "Which two flags does `fleet call` need? List them separated by commas.",
        "a": ["--model", "--prompt"],
        "grade": "set",
    },
]
