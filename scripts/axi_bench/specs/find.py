"""AXI bench spec: `find` -- where is a file by name.

On Linux there is no Search Everything (es.exe), so `find` answers with its bounded fallback
walk over ~/.local, ~/bin, /usr/local, /opt and home (HOME is the bench's throwaway one). The
answers below are this machine's: /usr/local/bin/starship exists and nothing is named
zz_no_such_file_qq; the /opt walk with a --limit is cut. The es.exe path itself is not benched
here; it needs Windows with Everything installed.
"""

VERB = "find"
SEED = []
RUNS = {
    "one": ["find", "starship"],
    "none": ["find", "zz_no_such_file_qq"],
    "cut": ["find", "rocm", "--limit", "3"],
    "preset": ["find", "starship", "--preset", "nope"],
}
EMPTY = ["find", "zz_no_such_file_qq"]
QUESTIONS = [
    {"run": "one", "q": "What is the full path of the match?", "a": "/usr/local/bin/starship", "grade": "exact"},
    {
        "run": "one",
        "q": "Was this answered by the Everything index or by a directory walk? Answer index or walk.",
        "a": "walk",
        "grade": "exact",
    },
    {"run": "none", "q": "How many matches were found?", "a": 0, "grade": "number"},
    {
        "run": "cut",
        "q": "Could more matches exist than the ones listed? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
    {
        "run": "preset",
        "q": "Is 'biggest' one of the allowed presets? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
]
