"""AXI bench spec: `scout` -- the read-only pre-flight, answered by a model.

Offline only: neither tree carries a .secrets/deepseek.key and the bench environment has no
DEEPSEEK_API_KEY, so the ask takes its closed-door path (a configuration state, no network) and
the bench measures what scout prints around it: the pack bounds, the filed verdict, the refusal
for a wearer with no resident ceremony, and the usage error."""

Q = ["is", "anyone", "working", "on", "core/axi"]
VERB = "scout"
SEED: list = []
RUNS = {
    "blind": ["scout", *Q, "--blind"],
    "resident": ["scout", *Q],
}
EMPTY = None  # an ask, not a listing
QUESTIONS = [
    {"run": "blind", "q": "Did the scout produce an answer? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "blind",
        "q": "Which credential is missing for the scout to answer? Answer in a few words.",
        "a": ["deepseek"],
        "grade": "contains",
    },
    {"run": "blind", "q": "How many in-flight tasks did the scout's pack hold?", "a": 24, "grade": "number"},
    {
        "run": "blind",
        "q": "What is the full command to adjudicate the verdict this scout filed? Give the command only.",
        "a": ["resident adjudicate scout-"],
        "grade": "contains",
    },
    {
        "run": "resident",
        "q": "Did the resident scout run? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
]
