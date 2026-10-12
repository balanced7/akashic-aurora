"""AXI bench spec: `web fetch` -- one page through the house web door, offline.

The bench never touches the network: the page is a fixture file served through a file:// URL,
which urllib opens locally, and the error run is a URL with no scheme, which fails before any
connection. `web search` has no offline path (it calls Brave or DuckDuckGo), so it is not benched.
"""

from pathlib import Path

PAGE = (Path(__file__).parent / "fixtures" / "web_page.html").resolve().as_uri()

VERB = "web fetch"
SEED = []
RUNS = {
    "page": ["web", "fetch", PAGE, "--limit", "600"],
    "bad": ["web", "fetch", "not-a-url"],
}
EMPTY = None
QUESTIONS = [
    {"run": "page", "q": "Which port does the staging cluster listen on?", "a": 7461, "grade": "number"},
    {"run": "page", "q": "What is the release codename named on this page?", "a": "unknown", "grade": "unknown"},
    {"run": "page", "q": "Does this output show the whole page text? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "page", "q": "How many characters of page text does this output show?", "a": 600, "grade": "number"},
    {
        "run": "page",
        "q": "What exact command would show the next part of this page? Give the command only.",
        "a": ["web fetch", "--offset 600"],
        "grade": "contains",
    },
    {"run": "bad", "q": "Did the fetch succeed? Answer yes or no.", "a": "no", "grade": "exact"},
]
