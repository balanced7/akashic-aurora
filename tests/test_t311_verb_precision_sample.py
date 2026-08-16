"""T311 precision ratchet -- the labelled sample that green pins could not replace.

Run: py tests/test_t311_verb_precision_sample.py   (or via pytest)

WHY THIS FILE EXISTS SEPARATELY FROM test_t311_capability_recall.py. Those pins all passed while
this sample measured a 67% FALSE POSITIVE RATE: 8 of the 12 triggers that should have stayed
silent fired a verb. Pins measure recall on cases the author imagined. Only a labelled sample of
REAL triggers measures precision -- and precision is what decides whether a pushed surface gets
read or skipped. A channel with perfect recall and 67% false positives is worse than no channel,
because it trains its reader to skip everything, including the true positives.

Every trigger below is real, taken from the 2026-08-15 session that motivated T311. Silence is a
first-class expected answer and is labelled as such (expected=None), because "correctly said
nothing" is the outcome this surface most needs to keep getting right.

This file is the regression instrument for the tuning, not for the feature. It has already earned
its keep once: the guard that killed the false positives also ate the URL in the captions trigger,
silencing the exact case the slice exists for, and this sample caught it on the next run.

Lesson: green_pins_are_not_a_good_gate_sample_the_false_positive_rate.
"""
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.at_action import _query_from, _verbs

# (trigger, expected) -- expected None means "must stay silent"; "a|b" means either is correct.
SAMPLE = [
    ("py tests/test_t311_capability_recall.py", None),
    ("git commit -F msgfile", None),
    ("git push origin master", None),
    ("py agent_cli.py boot claude", None),
    ("Get-ChildItem E:/ -Directory", None),
    ("git rm --cached chronicles/transcripts/20260811_priorish.jsonl", None),
    ("npm install", None),
    ("git status --porcelain", None),
    ("git ls-tree -r origin/master --name-only", None),
    ("Remove-Item X:/scratch.txt -Force", None),
    ("py scripts/bifrost_daemon.py --agent claude --manage-listener", None),
    ("py -m pytest tests/ -x", None),
    ("fetch https://www.youtube.com/watch?v=abc for the transcript", "captions"),
    ("this door is awkward, log the ergonomic friction", "friction|wish"),
    ("send a message to deepseek on the bus", "bifrost-send"),
    ("record a durable project decision for the next seat", "note"),
]

# Pre-registered bars. Set from the measurement AFTER the four guards landed, so a regression in
# either direction fails rather than being absorbed. Raising either bar is a decision that belongs
# in a commit message, not a quiet edit.
MAX_FALSE_POSITIVES = 0
MIN_HITS = 4


def _surfaced(cmd):
    return [v["verb"] for v in _verbs(_query_from(None, cmd, None, None), command=cmd)]


def test_verb_channel_precision_and_recall_hold():
    false_positives, hits, misses = [], 0, []
    for cmd, expected in SAMPLE:
        names = _surfaced(cmd)
        if expected is None:
            if names:
                false_positives.append((cmd, names))
        elif any(n in expected.split("|") for n in names):
            hits += 1
        else:
            misses.append((cmd, expected, names))

    assert len(false_positives) <= MAX_FALSE_POSITIVES, (
        f"verb channel got chatty: {len(false_positives)} false positive(s) "
        f"(bar {MAX_FALSE_POSITIVES}).\n  " + "\n  ".join(f"{c!r} -> {n}" for c, n in false_positives)
        + "\nA pushed surface that fires when it should not trains its reader to skip it.")
    assert hits >= MIN_HITS, (
        f"verb channel went deaf: {hits} hit(s), bar {MIN_HITS}. Missed:\n  "
        + "\n  ".join(f"{c!r} wanted {e}, got {n}" for c, e, n in misses))


def test_silence_is_the_common_case():
    """Most real triggers want nothing. If this surface ever speaks on a majority of commands it
    has stopped being a signal, whatever its accuracy on the cases it gets right."""
    spoke = sum(1 for cmd, _ in SAMPLE if _surfaced(cmd))
    assert spoke <= len(SAMPLE) // 2, (
        f"verb channel spoke on {spoke}/{len(SAMPLE)} triggers -- a surface that always speaks "
        "is a surface nobody reads")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"  FAIL  {name}\n        {e}")
    fp = sum(1 for c, e in SAMPLE if e is None and _surfaced(c))
    silent = sum(1 for c, e in SAMPLE if e is None)
    print(f"\nsample: {silent} should-stay-silent, {fp} false positive(s) "
          f"({100.0 * fp / max(1, silent):.0f}%)")
    sys.exit(1 if failures else 0)
