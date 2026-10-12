"""AXI bench spec: `bifrost-fetch` -- the full body behind a spilled `blob:<sha>` ref.

The seed sends an oversize body, which the send door spills to the blob store; the ref is
content-addressed (sha256 of the bytes, first 24 hex characters), so the spec can name it.
"""

import hashlib

BODY = "Release plan for the v2 parser. " + "Step: migrate one module, run the suite. " * 300 + "OWNER: carol."
REF = "blob:" + hashlib.sha256(BODY.encode("utf-8")).hexdigest()[:24]

VERB = "bifrost-fetch"
SEED = [["bifrost-send", "alice", BODY, "--to", "bob", "--kind", "note"]]
RUNS = {
    "blob": ["bifrost-fetch", "--get", REF],
    "out": ["bifrost-fetch", "--get", REF, "--out", "/dev/null"],
    "miss": ["bifrost-fetch", "--get", "9999999999999-0"],
    "usage": ["bifrost-fetch"],
}
EMPTY = None  # a fetch has no empty state: a ref resolves or it is a NOT_FOUND error
QUESTIONS = [
    {"run": "blob", "q": "Who is named as the owner at the end of the release plan?", "a": "carol", "grade": "exact"},
    {"run": "out", "q": "How many bytes were written?", "a": len(BODY.encode("utf-8")), "grade": "number"},
    {"run": "miss", "q": "Was the message found? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "usage",
        "q": "What argument must be added to this command for it to work? Give the flag only.",
        "a": "--get",
        "grade": "contains",
    },
]
