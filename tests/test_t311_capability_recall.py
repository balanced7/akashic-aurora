"""T311 RED pins -- capability-recall: recall-at must carry VERBS, not only lessons and locks.

Run: py tests/test_t311_capability_recall.py   (or via pytest)

WHY THIS EXISTS, with the receipt. On 2026-08-15 a seat met a YouTube URL, reached for WebFetch,
then grepped the repo for a script -- while `py agent_cli.py captions <url>` sat on the door with
W154 tests behind it. The operator had to type "its a verb", then: "We forget it every time Q__Q".
Measured the same session: 85 verbs on the door, that seat used 14.

`discover --semantic` was asked whether this capability already exists and answered
EXISTS:partially -- core/recall/at_action.py is the unasked moment-of-need push channel but it
carries only lessons and locks, and `discover` itself is the NEAREST MISS because it is a flat
self-serve listing the agent must already know to ask for. This slice adds the missing cargo to
the existing channel rather than opening a second door, matching _query_from's own docstring:
"Extending this one function rather than adding a second door is deliberate."

THE DISCIPLINE THESE PINS ENCODE
  1. the trigger that failed in the wild now surfaces its verb (captions),
  2. a felt-friction trigger surfaces the friction/wish organs the same seat also never reached for,
  3. a capability shipped as a FLAG is reachable -- the structural blind spot recorded in lesson
     discover_reads_verbs_not_flags, which `discover` cannot see past because it reads the verb
     table and module index, never add_argument help,
  4. NOISE FLOOR: an unrelated trigger surfaces ZERO verbs. Calibrated silence is a stated feature
     of this surface ("downstream silence is CALIBRATED, not a dead hook") and a chatty organ gets
     ignored, which would cost more than it pays,
  5. the index is derived from the PARSER, never a snapshot file, so it cannot drift (the T115
     check_advertised_verbs precedent: verbs parsed from agent_cli's AST),
  6. verbs are capped and never displace a lesson.

Pin 4 is a pin that must STAY green, not go green -- it passes vacuously today and its whole job
is to fail the day the verb channel gets chatty.
"""
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.at_action import recall_at, render


class _FakeStore:
    """Injected so these pins never touch canonical Redis (test_recall_at.py precedent)."""
    def __init__(self, recs):
        self._recs = recs

    def load_all_learnings_from_store(self):
        return list(self._recs)


_STORE = _FakeStore([
    {"experiment_name": "unrelated_lesson", "success": "yes",
     "recommendation": "this lesson exists only so the lesson channel is non-empty"},
])


def _verbs_from(res):
    """Verb names out of a recall_at result, tolerating the pre-build shape (no 'verbs' key)."""
    return [v.get("verb") for v in (res.get("verbs") or []) if isinstance(v, dict)]


def test_youtube_trigger_surfaces_the_captions_verb():
    """The exact 2026-08-15 failure, made falsifiable."""
    res = recall_at(
        command="fetch https://www.youtube.com/watch?v=p1DviQ9mva0 to read the transcript",
        learning_store=_STORE)
    verbs = _verbs_from(res)
    assert "captions" in verbs, (
        f"expected the captions verb to be pushed at a youtube trigger, got {verbs}. "
        "This is the failure that motivated T311: the seat grepped for a script instead.")


def test_felt_friction_surfaces_the_friction_or_wish_verb():
    """The operator has a standing directive to log friction the moment it is felt; the same
    session felt it four times and filed lessons instead, because neither organ was reachable."""
    res = recall_at(
        command="this door is awkward and cost me three attempts, log the ergonomic friction",
        learning_store=_STORE)
    verbs = _verbs_from(res)
    assert ("friction" in verbs) or ("wish" in verbs), (
        f"expected the friction or wish organ to surface at felt friction, got {verbs}")


def test_flag_shipped_capability_is_reachable():
    """Closes the blind spot in the sibling organ: `discover` reads the verb table and module
    index, so a capability shipped as a FLAG on an existing verb is invisible to it
    (lesson discover_reads_verbs_not_flags). The verb index must read add_argument help."""
    try:
        from core.recall.at_action import verb_index
    except ImportError as e:
        raise AssertionError(
            "verb_index() does not exist yet -- T311 must expose a parser-derived index "
            f"that includes flag help strings, not only verb names ({e})")
    idx = verb_index()
    hay = " ".join(
        f"{e.get('verb', '')} {e.get('purpose', '')} {' '.join(e.get('flags', []) or [])}"
        for e in idx).lower()
    assert "resident" in hay, (
        "expected flag-level capabilities (e.g. ask's --as-resident) to be indexed; "
        "a verb-name-only index reproduces exactly what discover already cannot see")


def test_index_is_derived_from_the_parser_not_a_snapshot():
    """T115 precedent: parse agent_cli's AST so the index cannot drift from the parser.
    A snapshot file is a second source of truth and will rot."""
    try:
        from core.recall.at_action import verb_index
    except ImportError as e:
        raise AssertionError(f"verb_index() does not exist yet ({e})")
    idx = verb_index()
    names = {e.get("verb") for e in idx}
    for known in ("captions", "discover", "recall-at", "wish"):
        assert known in names, (
            f"{known!r} missing from the parser-derived verb index -- got {len(names)} verbs. "
            "If this index came from a snapshot file it is already the wrong design.")


def test_noise_floor_unrelated_trigger_surfaces_no_verbs():
    """MUST STAY GREEN. Passes vacuously before the build; its job is to fail the day the verb
    channel becomes chatty. Silence beats noise on this surface, by stated design."""
    res = recall_at(command="run the bbbbb qqqqq zzzzz widget", learning_store=_STORE)
    assert _verbs_from(res) == [], (
        f"an unrelated trigger must surface ZERO verbs, got {_verbs_from(res)}")


def test_verbs_are_capped_and_never_displace_lessons():
    """The lesson channel is the proven one. Verbs ride along; they do not take its seats."""
    res = recall_at(
        command="fetch https://www.youtube.com/watch?v=p1DviQ9mva0 transcript and log the friction "
                "and discover what else the door can do and note it and learn from it",
        learning_store=_STORE)
    verbs = _verbs_from(res)
    assert len(verbs) <= 2, f"verb channel must cap at 2, got {len(verbs)}: {verbs}"
    assert "lessons" in res, "the lesson channel must survive the addition of verbs"


def test_render_includes_verbs_without_breaking_empty_case():
    """render() must stay factual and still return '' for a genuinely empty result."""
    empty = recall_at(command="qqqqq zzzzz bbbbb", learning_store=_STORE)
    assert render(empty) == "", "empty result must still render as the empty string"
    res = recall_at(
        command="fetch https://www.youtube.com/watch?v=p1DviQ9mva0 for the transcript",
        learning_store=_STORE)
    out = render(res)
    assert "captions" in out, (
        f"the rendered surface must name the verb the agent should reach for, got: {out!r}")


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
    print(f"\n{failures} failing pin(s) -- RED is the expected state before T311 is built.")
    sys.exit(1 if failures else 0)
