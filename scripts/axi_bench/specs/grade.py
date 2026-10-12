"""AXI bench spec: `grade` -- graders and verdicts, on their offline paths.

`grade run --judge` calls model graders and is never run here. The runs cover the power
calculation, grader calibration (labels seeded with `grade label`, which only appends a line),
`grade run` and `grade compare` with no replay runs to read (no model, no tests run)."""

VERB = "grade"
SEED = [
    ["grade", "label", "--criterion", "quality", "--person", "better", "--judge-call", "better", "--ref", "r1"],
    ["grade", "label", "--criterion", "quality", "--person", "worse", "--judge-call", "better", "--ref", "r2"],
    ["grade", "label", "--criterion", "process", "--person", "same", "--judge-call", "same", "--ref", "r3"],
]
RUNS = {
    "power": ["grade", "power", "--scenarios-n", "40", "--trials", "3", "--delta", "0.15"],
    "agreement": ["grade", "agreement"],
    "run_none": ["grade", "run", "--candidate", "baseline", "--scenario", "T1-abc"],
    "compare": ["grade", "compare", "--candidate", "opus-high", "--against", "baseline", "--scenario", "T1-abc"],
}
EMPTY = ["grade", "run", "--candidate", "baseline", "--scenario", "T1-abc"]
QUESTIONS = [
    {
        "run": "power",
        "q": "What is the smallest pass-rate change, in percentage points, that this design detects at 80% "
        "power? Give the number only.",
        "a": 17.5,
        "grade": "number",
    },
    {"run": "agreement", "q": "How many person labels exist for the quality grader?", "a": 2, "grade": "number"},
    {
        "run": "agreement",
        "q": "Is the quality grader calibrated, so its verdicts count? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {"run": "run_none", "q": "How many runs were graded?", "a": 0, "grade": "number"},
    {
        "run": "compare",
        "q": "What is the overall (Pareto) verdict of opus-high against baseline?",
        "a": "no difference shown",
        "grade": "exact",
    },
]
