"""RED pins: the ranker matches against 42% of the lesson corpus and nothing says so.

THE MEASUREMENT. `_project_items` (core/recall/at_action.py:367-372) takes the FIRST of
`recommendation`, `actual`, `what_tried` and breaks. Measured over all 1,562 lessons,
2026-10-03, by replaying that exact loop:

    recommendation   1,509 rows carry it, chosen on 1,509   (98.4% of 1,534 projected)
    actual           1,503 rows carry it, chosen on    25   ( 1.6%)
    what_tried       1,533 rows carry it, chosen on     0   ( 0.0%)

    characters across the three fields   1,925,277
    characters any query can match       814,540
    characters invisible to every query  1,110,737   =  57.7%

`what_tried` is present on 1,533 of 1,562 lessons and can never be matched, because one of
the other two always precedes it in the loop. A field filled on 98% of the corpus that no
query can ever touch.

WHY THE OBVIOUS FIX IS WRONG, AND THE CODE SAYS SO. "Just concatenate the three" was the
first proposal. The comment directly above the loop refuses it: "`recommendation` is
forward-looking advice (a claim), `actual` is an observed outcome (evidence), `what_tried` is
the action. The reader must be able to tell a claim from evidence, so carry the field through
(-> _provenance_tag)." That distinction is worth more than the retrieval it would buy, and
`_provenance_tag` (at_action.py:1938) renders it to the seat on every surfaced lesson.

SO THE CONTRACT IS: MATCHING WIDENS, DISPLAY DOES NOT. One `match_text` spanning all three
fields feeds `_item_tokens` (at_action.py:590, the single seam where an item becomes
matchable tokens); `text` stays the one provenance-tagged field the reader is shown. The
ranker gets 1.9M characters; the reader still gets told whether it is looking at a claim or
at evidence. A surface may widen WHAT IT MATCHES; it may not widen WHAT IT CLAIMS TO BE.

These pins exist because that distinction is exactly the kind a later simplification
collapses: concatenating into `text` would make every pin here pass except the display ones.

Run::

    py -m pytest tests/test_match_surface_spans_every_text_field.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.recall import at_action as A  # noqa: E402


REC = {
    "experiment_name": "a_lesson_with_all_three_fields",
    "recommendation": "Use when zebrafish surface unexpectedly in the pipeline.",
    "actual": "the quokka counter overflowed after nine runs",
    "what_tried": "ran the narwhal probe against a cold store",
    "success": "yes",
    "agent_id": "t-seat",
}


def _only(recs):
    items = A._project_items(recs)
    assert len(items) == 1, "expected exactly one projected item, got %d" % len(items)
    return items[0]


# --------------------------------------------------------------- matching widens
def test_a_token_only_in_what_tried_is_matchable():
    """THE PIN. `what_tried` is carried by 1,533 lessons and chosen as match text by ZERO.
    'narwhal' appears only there."""
    toks = A._item_tokens(_only([dict(REC)]))
    assert "narwhal" in toks, (
        "a token present only in what_tried is not matchable -- 1,533 lessons carry that "
        "field and no query can reach any of them. got: %s" % sorted(toks))


def test_a_token_only_in_actual_is_matchable():
    """`actual` is the longest field in the schema (726,002 chars) and wins the loop on 25
    of 1,534 rows."""
    toks = A._item_tokens(_only([dict(REC)]))
    assert "quokka" in toks, sorted(toks)


def test_the_recommendation_is_still_matchable():
    """RATCHET. Widening must not drop what already worked."""
    toks = A._item_tokens(_only([dict(REC)]))
    assert "zebrafish" in toks, sorted(toks)


def test_a_lesson_carrying_only_what_tried_is_still_projected_and_matchable():
    """The loop's `if not summary: continue` drops a record with no recommendation and no
    actual. Such a lesson is invisible entirely, not merely unmatched."""
    rec = {"experiment_name": "only_the_action_was_recorded",
           "what_tried": "ran the narwhal probe", "success": "yes"}
    items = A._project_items([rec])
    assert items, "a lesson carrying only what_tried was dropped from the projection entirely"
    assert "narwhal" in A._item_tokens(items[0]), sorted(A._item_tokens(items[0]))


# --------------------------------------------------------------- display does NOT widen
def test_the_displayed_text_is_still_one_field_not_three():
    """THE GUARD AGAINST THE EASY WRONG FIX. Concatenating into `text` would satisfy every
    matching pin above and silently destroy the claim-versus-evidence distinction that
    _provenance_tag renders. The displayed text must remain exactly the chosen field."""
    it = _only([dict(REC)])
    assert it["text"] == REC["recommendation"], (
        "the displayed text is no longer the single provenance-tagged field: %r" % it["text"])
    assert "quokka" not in it["text"], "evidence leaked into the displayed claim"
    assert "narwhal" not in it["text"], "the action leaked into the displayed claim"


def test_the_field_tag_still_names_where_the_displayed_text_came_from():
    """_provenance_tag reads item['field'] to tell a seat whether it is reading a claim or
    an observation. Widening the match surface must not blur that."""
    assert _only([dict(REC)])["field"] == "recommendation"
    no_rec = {k: v for k, v in REC.items() if k != "recommendation"}
    assert _only([no_rec])["field"] == "actual"


def test_provenance_tag_is_unchanged_by_the_widening():
    """RATCHET on the rendered surface, not just the field: the seat must see the same tag."""
    it = _only([dict(REC)])
    tag = A._provenance_tag(it)
    assert tag and isinstance(tag, str), tag
    assert "quokka" not in tag and "narwhal" not in tag, tag


# --------------------------------------------------------------- the seam itself
def test_the_match_surface_is_carried_as_its_own_field():
    """Names the intended shape, so a refactor that folds matching back into `text` fails
    here with WHICH piece is missing rather than only that recall drifted."""
    it = _only([dict(REC)])
    blob = str(it.get("match_text") or "")
    for token in ("zebrafish", "quokka", "narwhal"):
        assert token in blob, "match_text does not span all three fields (missing %r)" % token


def test_item_tokens_reads_the_match_surface():
    """_item_tokens (at_action.py:590) is the ONE seam where an item becomes matchable
    tokens. A match_text nothing reads is the unwired-keystone shape."""
    import inspect
    src = inspect.getsource(A._item_tokens)
    assert "match_text" in src, (
        "_item_tokens does not read match_text -- the field would be inert, which is the "
        "'looks adopted but is not load-bearing' failure")
