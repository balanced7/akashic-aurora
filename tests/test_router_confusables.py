"""
Slice D2 -- word-boundary matching for TrackRouter + ThemeAssigner.

Bar: keywords match as WHOLE WORDS only (a keyword can't fire inside a larger word), and the
genuinely-ambiguous bare "comfy" no longer false-routes. The gold-fixture ARI bar is enforced
by tests/test_track_router.py::test_meets_acceptance_bar (must stay green = no regression).

These are the worst-case confusables the substring matcher got wrong (probe A) plus the
positive cases that MUST still match.  Run: py -m pytest tests/test_router_confusables.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.narrative.track_router import TrackRouter, RouteHint
from core.narrative.theme_assigner import ThemeAssigner
from core.narrative.schema import Beat

R = TrackRouter()
TH = ThemeAssigner()


def _route(text, *, category="", task=""):
    b = Beat(id="x", at="2026-01-01T00:00:00", kind="note", summary=text, source="s")
    return R.route_one(b, RouteHint(category=category, task=task))


def _themes(text):
    return TH.assign(Beat(id="x", at="2026-01-01T00:00:00", kind="note", summary=text, source="s"))


def test_confusables_do_not_false_route():
    """Substring false positives the old matcher produced -- now must NOT fire a keyword."""
    confusables = [
        "comfy sweater knitting notes",      # 'comfy' (dropped) -- was vision
        "the restore button was grey",       # 'store' inside 'restore' -- was ai-setup
        "paperwork for the taxes",           # 'paper' inside 'paperwork' -- was research
        "the speaker plays at 50 watts",     # 'tts' inside 'watts' -- was voice
        "a vocalist practiced scales",       # 'vocals' not a word here -- was stemroller
    ]
    for text in confusables:
        res = _route(text)
        assert res.basis in ("persist", "unknown"), \
            f"'{text}' should NOT match a keyword, got {res.track} via {res.basis}"


def test_whole_word_keywords_still_match():
    """Real keywords as whole words MUST still route (precision, not blanket suppression)."""
    cases = [
        ("running stemroller to split vocals", "stemroller", "strong"),
        ("comfyui workflow crashed", "vision", "strong"),
        ("a comfy ui workflow note", "vision", "strong"),      # the phrase form
        ("stem separation pipeline", "stemroller", "strong"),
        ("read a paper on raptor indexing", "research", "generic"),
        ("the redis store keeps state", "ai-setup", "generic"),
    ]
    for text, track, basis in cases:
        res = _route(text)
        assert res.track == track and res.basis == basis, \
            f"'{text}' -> expected {track}/{basis}, got {res.track}/{res.basis}"


def test_phrase_keywords_keep_internal_spaces():
    """A multi-word keyword still matches across its space, but not when split by other words."""
    assert _route("we did stem separation today").track == "stemroller"
    # 'stem' and 'separation' present but NOT adjacent -> the phrase must not match
    res = _route("the stem of the plant and a separation of concerns")
    assert res.basis in ("persist", "unknown"), f"non-adjacent phrase must not match, got {res.basis}"


def test_theme_word_boundary():
    """ThemeAssigner is multi-label but also word-boundary: 'store' must not fire on 'restore'."""
    assert "memory" in _themes("the memory store keeps recall fast")     # whole word
    assert "memory" not in _themes("please restore the earlier version")  # 'store' inside 'restore'
    assert "narrative" in _themes("the story spine and its atlas")        # whole words
    assert _themes("just some unrelated text") == []                      # no keyword -> no theme


if __name__ == "__main__":
    for fn in [test_confusables_do_not_false_route, test_whole_word_keywords_still_match,
               test_phrase_keywords_keep_internal_spaces, test_theme_word_boundary]:
        fn()
    print("ALL D2 CONFUSABLE TESTS PASSED")
