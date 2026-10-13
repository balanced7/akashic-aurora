"""AXI bench spec: `eye` -- the transcript index: ingest, find, stats, freq, trace, standing, get.

THE CORPUS. The eye indexes every transcript under ~/.claude/projects (HOME is the bench's
throwaway one, so that root is empty) plus the archive roots named by
AKASHIC_TRANSCRIPT_ARCHIVE_ROOTS. This spec points that variable at the repo's own eye fixtures
(tests/fixtures/eye, eight small sessions), read-only, so the seeded `eye ingest` indexes exactly
those. The index itself lands in the sandbox's AURORA_HOME (state/eye/eye.db under the world's
home), never in the checkout's state/eye, which in a worktree links to the live index.

Not benched: `route save` and `route walk`, which append to state/coord/routes.jsonl beside the
code; their renders are pinned by tests/test_t335_s2_the_render_the_acceptance_promised.py.
"""

import os
from pathlib import Path

os.environ["AKASHIC_TRANSCRIPT_ARCHIVE_ROOTS"] = str(Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "eye")

VERB = "eye find"  # the leaf: `eye` itself hands its flags to its subcommands
SEED = [["eye", "ingest"]]
RUNS = {
    "find": ["eye", "find", "sword"],
    "find_cut": ["eye", "find", "sword", "--limit", "2"],
    "stats": ["eye", "stats"],
    "freq": ["eye", "freq", "sword"],
    "trace": ["eye", "trace", "session_gamma:5"],
    "standing": ["eye", "standing"],
    "get_missing": ["eye", "get", "nope:1"],
}
EMPTY = ["eye", "find", "sword"]
QUESTIONS = [
    {"run": "find", "q": "How many events match the phrase in total?", "a": 5, "grade": "number"},
    {
        "run": "find_cut",
        "q": "Are all of the matching events listed in this output? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {"run": "stats", "q": "How many indexed events are in the operator voice?", "a": 23, "grade": "number"},
    {
        "run": "freq",
        "q": "What verdict did the frequency check reach? Give the verdict only.",
        "a": "standing-directive",
        "grade": "exact",
    },
    {
        "run": "trace",
        "q": "How many records make up the same utterance as the traced event?",
        "a": 3,
        "grade": "number",
    },
    {
        "run": "standing",
        "q": "Which recurring directive does no durable plane cite? Quote the phrase.",
        "a": "always fence the migration path before shipping it",
        "grade": "contains",
    },
    {"run": "get_missing", "q": "Was an event found at the address? Answer yes or no.", "a": "no", "grade": "exact"},
]
