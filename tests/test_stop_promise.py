"""Stop-hook promise check (agent/harness/hooks/claude_stop.py) -- the last-paragraph audit.

The discipline (first-party fold-in 2026-07-08): a turn may not END on a promise of future
work. High precision beats recall here -- a false bounce teaches the model to distrust the
hook -- so questions, user-conditional endings, and plain outcome statements must never match.
Once per session (latch), scope-gated, kill-switched, fail-open.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.harness.hooks.claude_stop import (final_paragraph, promise_shaped,
                                       last_assistant_text, _promise_block)


def test_promise_positive_cases():
    for p in ("I'll write the report next.",
              "I will run the suite and fix what breaks.",
              "Now I'll wire the hook.",
              "Next, I'll update the docs.",
              "- I'll run the tests",
              "I'm going to refactor the seam."):
        assert promise_shaped(p), f"should bounce: {p!r}"
    print("--- promise positives ---\n  first-person future-work openers bounce OK")


def test_promise_negative_cases():
    for p in ("Done: the fix is committed and the suite is green.",
              "Which slice do you want first?",
              "Say the word and I'll start with the design doc.",
              "Once you approve, I'll ship it.",
              "Let me know if the numbers look off.",
              "Blocked on the API key; stopping here.",
              "The tests pass; task complete.",
              ""):
        assert not promise_shaped(p), f"must NOT bounce: {p!r}"
    print("--- promise negatives ---\n  questions/user-conditional/outcomes never bounce OK")


def test_stop_verbs_are_endings_not_promises():
    """DeepSeek review finding 1: 'I'll <stop-verb>' is an outcome in future-tense clothing."""
    for p in ("I'll wait for your review.",
              "I'll pause here.",
              "I'll stop for now.",
              "I'll hold off until the numbers land.",
              "I'll defer to the design doc on this one.",
              "I'll leave it there."):
        assert not promise_shaped(p), f"stop-verb ending must NOT bounce: {p!r}"
    # the carve-out must not create false NEGATIVES: ambiguous verbs stay bounceable
    for p in ("I'll keep working on the parser.",
              "I'll write the fix and run the tests next."):
        assert promise_shaped(p), f"real future work must still bounce: {p!r}"
    print("--- stop verbs ---\n  wait/pause/stop/hold/defer endings pass; 'keep working' still bounces OK")


def test_final_paragraph_extraction():
    assert final_paragraph("one\n\ntwo lines here") == "two lines here"
    assert final_paragraph("The fix:\n\n```python\nprint('x')\n```") == "The fix:", \
        "a trailing code fence is not prose -- audit the paragraph above it"
    assert final_paragraph("") == ""
    print("--- final paragraph ---\n  last prose block; fences skipped; empty-safe OK")


def test_last_assistant_text_reads_tail():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {}}]}}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Done.\n\nI'll deploy next."}]}}) + "\n")
    out = last_assistant_text(p)
    assert "I'll deploy next." in out, out
    assert promise_shaped(final_paragraph(out)), "end-to-end: transcript tail -> bounceable excerpt"
    assert last_assistant_text(os.path.join(d, "missing.jsonl")) == "", "missing file -> '' (fail-open)"
    print("--- transcript tail ---\n  last assistant TEXT message wins; tool-only entries skipped OK")


def test_promise_block_fails_open():
    assert _promise_block({}) is None, "no payload -> no block (fail-open)"
    assert _promise_block({"session_id": "s", "transcript_path": ""}) is None
    print("--- fail-open ---\n  empty/partial payload never blocks OK")


if __name__ == "__main__":
    print("=" * 60)
    print("STOP-HOOK PROMISE CHECK")
    print("=" * 60)
    test_promise_positive_cases()
    test_promise_negative_cases()
    test_stop_verbs_are_endings_not_promises()
    test_final_paragraph_extraction()
    test_last_assistant_text_reads_tail()
    test_promise_block_fails_open()
    print("\nALL STOP-PROMISE TESTS PASSED")
