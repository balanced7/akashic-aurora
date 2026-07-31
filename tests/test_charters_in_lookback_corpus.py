"""charters/ must be in the lookback corpus -- the retrieval plane must reach what was MEANT.

VERIFIED DEFECT (2026-07-31, design capture section 3): `lookback` searched docs, research,
notes, promoted, chapters and git. `charters/` was in NONE of them. A search for
"handoff ergonomics between departments" returned nothing, for a phrase appearing verbatim at
charters/daniel/INTERIORITY.md:347. Daniil's twenty interiority entries -- and every seat's --
were unreachable through the primary search door. You could only find them by already knowing
the path, which a newcomer by definition does not.

The deeper cut, and the reason this is a corpus bug and not a ranking one: the corpus covered
what was DONE (docs, git, chapters) and not what was MEANT (charters). Those are different
planes, so charters gets its OWN layer rather than competing with the numerous docs for the
same three per-layer slots -- adding it to `docs` would have left it technically present and
practically still unreachable.

Ordering constraint (guarded by P3): `docs` must stay LAYERS[0] -- lookback's query counter
keys off the first layer name (`if layer == LAYERS[0][0]: bump("lookback:queries", 1)`), so
prepending a layer would silently corrupt the counter.
"""
import os
import pytest

from core.recall import lookback as lb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIORITY = os.path.join(ROOT, "charters", "daniel", "INTERIORITY.md")


@pytest.mark.skipif(not os.path.exists(INTERIORITY),
                    reason="needs the real repo corpus (charters/daniel/INTERIORITY.md)")
def test_p1_charters_are_a_lookback_layer():
    """The registered layer exists and loads items. THE defect, at its root."""
    names = [n for n, _ in lb.LAYERS]
    assert "charters" in names, f"charters/ is outside the lookback corpus; layers: {names}"

    items = dict(lb.LAYERS)["charters"]()
    assert items, "charters layer registered but loads nothing"
    sources = {it["source"] for it in items}
    assert any(s.startswith("charters/") for s in sources), \
        f"charters layer returns non-charter sources: {sorted(sources)[:5]}"


@pytest.mark.skipif(not os.path.exists(INTERIORITY),
                    reason="needs the real repo corpus (charters/daniel/INTERIORITY.md)")
def test_p2_the_exact_question_that_returned_nothing_now_answers():
    """The live reproduction from the capture. This is the pin that would have caught it."""
    hits = lb.lookback("handoff ergonomics between departments")
    assert hits, "no hits at all for a question the charters corpus answers verbatim"
    charter_hits = [h for h in hits if str(h.get("source", "")).startswith("charters/")]
    assert charter_hits, (
        "the phrase appears verbatim at charters/daniel/INTERIORITY.md:347 and lookback "
        f"still cannot reach it. Sources returned: {[h.get('source') for h in hits][:8]}")


@pytest.mark.skipif(not os.path.exists(INTERIORITY),
                    reason="needs the real repo corpus")
def test_p3_docs_stays_first_so_the_query_counter_is_not_corrupted():
    """lookback bumps 'lookback:queries' on LAYERS[0]; charters must not displace docs."""
    assert lb.LAYERS[0][0] == "docs", (
        "docs must remain the first layer -- the query counter keys off LAYERS[0][0]; "
        f"got {lb.LAYERS[0][0]}")


@pytest.mark.skipif(not os.path.exists(INTERIORITY),
                    reason="needs the real repo corpus")
def test_p4_charter_layer_is_fail_soft_like_every_other_adapter():
    """A broken corpus drops out; lookback never bricks (the adapter contract, line 149)."""
    loader = dict(lb.LAYERS)["charters"]
    real = lb.ROOT
    try:
        lb.ROOT = os.path.join(ROOT, "no_such_dir_for_this_pin")
        assert loader() == [], "charters adapter must return [] when its tree is absent"
    finally:
        lb.ROOT = real
