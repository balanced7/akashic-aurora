"""AXI bench spec: `list` -- every lesson in memory (recall with no query)."""

VERB = "list"
SEED = [
    ["learn", "bench", "--experiment", f"filler_{i:02d}", "--tried", "a", "--result", "b",
     "--recommend", f"Lesson number {i}.", "--category", "testing" if i % 2 else "docs"]
    for i in range(1, 29)
]  # fmt: skip
RUNS = {"all": ["list"]}
EMPTY = ["list"]
QUESTIONS = [
    {"run": "all", "q": "How many lessons are stored in memory in total?", "a": 28, "grade": "number"},
    {"run": "all", "q": "Does this output show every stored lesson? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "all", "q": "Which category is the lesson filler_07 in?", "a": "testing", "grade": "exact"},
    {"run": "all", "q": "How many lessons does this output show?", "a": 25, "grade": "number"},
]
