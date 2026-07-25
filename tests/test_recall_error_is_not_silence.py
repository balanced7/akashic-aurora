"""Pin: a recall FAILURE must never render as confident silence.

FOUND BY CODEX, 2026-07-25, and reproduced here. core/recall/at_action.py's top-level
exception handler returned:

    {"lessons": [], "faithful": True, "confidence": 1.0, "error": type(e).__name__}

So a RuntimeError inside retrieval came back as "I looked thoroughly and there is genuinely
nothing relevant, with full confidence." The `error` key was set at line 1182 and read
NOWHERE -- no consumer, no render, no counter. The failure marker existed and nothing looked
at it, so the hook printed its ordinary nothing-relevant silence.

This is the sixth instance of one genus today, and the worst-placed: it sits in the recall hot
path, which fires before every edit and command. Every silent injection could have been a
masked failure, and there was no way to tell from the outside.

The others, for the record: a token meter printing a confident zero while recording nothing; a
door-parity parser seeing 0 verbs and passing everything; a census OK-line over nothing
examined; a directory pointer resolving to the wrong contents; and an isolation flag treated
as proof of a redirect that never happened.

THE RULE: faithful and confidence describe a check that RAN. When retrieval fails, they are
UNAVAILABLE -- not True, not 1.0. Silence that means "nothing relevant" and silence that means
"I could not look" are different facts and must not share a rendering.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core.recall.at_action as aa  # noqa: E402


def _force_failure(monkeypatch):
    """Make the retrieval body raise, leaving the top-level handler to answer."""
    def boom(*a, **k):
        raise RuntimeError("store unreachable")
    monkeypatch.setattr(aa, "_query_from", boom, raising=False)


def test_a_failed_recall_does_not_claim_faithfulness(monkeypatch):
    _force_failure(monkeypatch)
    out = aa.recall_at(path="core/foundation/store.py")
    assert out.get("error"), "the failure must be recorded"
    assert out.get("faithful") is not True, (
        "a retrieval that RAISED claimed faithful=True -- it verified nothing"
    )


def test_a_failed_recall_does_not_claim_full_confidence(monkeypatch):
    _force_failure(monkeypatch)
    out = aa.recall_at(path="core/foundation/store.py")
    assert out.get("confidence") != 1.0, (
        "a retrieval that RAISED claimed confidence=1.0 -- the confident-zero genus"
    )


def test_the_error_is_visible_to_a_renderer(monkeypatch):
    """The marker existed and nothing read it. Rendering must not print ordinary silence."""
    _force_failure(monkeypatch)
    out = aa.recall_at(path="core/foundation/store.py")
    rendered = aa.render(out)
    assert rendered, "a failed recall must render SOMETHING, not empty silence"
    low = rendered.lower()
    assert ("error" in low or "unavailable" in low or "could not" in low), (
        f"a failed recall rendered as ordinary silence: {rendered!r}"
    )


def test_a_genuinely_empty_recall_still_renders_silently():
    """The fix must not turn honest 'nothing relevant' into noise -- that is the whole design."""
    out = {"path": "x", "command": None, "query": "", "lessons": [], "locks": [],
           "counter": None, "shown": 0, "total": 0, "faithful": True, "confidence": 1.0}
    rendered = aa.render(out)
    assert not rendered, "a true empty must stay silent -- silence-when-irrelevant is the contract"
