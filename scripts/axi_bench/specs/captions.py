"""AXI bench spec: `captions` -- the missing-dependency path, offline.

A real run calls yt-dlp, which fetches from YouTube. The bench runs only where yt-dlp is NOT
importable, so the verb stops at its setup error before anything leaves the machine; the spec
refuses to load where yt-dlp is installed. The success and no-tracks shapes are pinned by
tests/test_axi_captions.py with a fake fetch.
"""

import importlib.util

if importlib.util.find_spec("yt_dlp") is not None:
    raise SystemExit("captions bench refused: yt-dlp is importable here, so a run would fetch from YouTube")

VERB = "captions"
SEED = []
RUNS = {"missing": ["captions", "https://www.youtube.com/watch?v=aaaaaaaaaaa"]}
EMPTY = None
QUESTIONS = [
    {"run": "missing", "q": "Were any caption files written? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "missing",
        "q": "Which tool is missing? Give its name only.",
        "a": "yt-dlp",
        "grade": "exact",
    },
    {
        "run": "missing",
        "q": "What exact command installs the missing tool? Give the command only.",
        "a": ["install", "yt-dlp"],
        "grade": "contains",
    },
]
