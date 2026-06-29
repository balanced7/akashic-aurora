"""Characterization tests for recall-at-action (core/recall/at_action.py).

Run: py tests/test_recall_at.py   (or via pytest)

The discipline this must prove (SOTA-informed, docs/agent-experience-plan.md + the research):
  - a RELEVANT path/command surfaces the matching active lesson with a source pointer,
  - SHOW NOTHING when nothing clears the relevance floor (never pad to `limit`) — silence beats noise,
  - dedup by source (one line per experiment),
  - the query builder drops generic/short tokens,
  - render() formats locks + lessons factually and returns '' for an empty result,
  - the whole thing FAILS SOFT (no path/command, bad input -> empty, never raises).

Uses an injected fake learning store so it never touches canonical Redis, and `command=` (not
`path=`) so it never reaches the lock/bus layer.
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.at_action import recall_at, render, _query_from


class _FakeStore:
    def __init__(self, recs):
        self._recs = recs
    def load_all_learnings_from_store(self):
        return list(self._recs)


_STORE = _FakeStore([
    {"experiment_name": "spine1_unify", "success": "yes",
     "recommendation": "the consolidator is the one seam; route every source through it"},
    {"experiment_name": "redis_probe", "success": "no",
     "recommendation": "probe reachability first; a filtered port hangs connect for 48s"},
    {"experiment_name": "perf_memo", "success": "yes",
     "recommendation": "memoization gave a real speedup; loop unrolling did not"},
])


def test_relevant_command_surfaces_the_matching_lesson():
    res = recall_at(command="edit core/primitives/consolidator.py now", learning_store=_STORE)
    srcs = [l["source"] for l in res["lessons"]]
    assert "learn:experiment:spine1_unify" in srcs, f"expected the consolidator lesson, got {srcs}"
    assert res["faithful"] is True and res["shown"] >= 1
    print(f"\n--- relevant ---\n  consolidator action -> {srcs} OK")


def test_show_nothing_when_irrelevant():
    res = recall_at(command="run the bbbbb qqqqq zzzzz widget", learning_store=_STORE)
    assert res["lessons"] == [] and res["shown"] == 0, f"should surface nothing, got {res}"
    print("--- show-nothing ---\n  no relevant lesson -> silence (no padding) OK")


def test_never_pads_to_limit():
    # query matches exactly one lesson ('memoization'); limit=3 must still return only the 1 match.
    res = recall_at(command="apply memoization to the hot loop", limit=3, learning_store=_STORE)
    assert len(res["lessons"]) == 1 and res["lessons"][0]["source"] == "learn:experiment:perf_memo", res
    print("--- no padding ---\n  one match under limit=3 -> exactly 1 surfaced OK")


def test_dedup_by_source():
    dup = _FakeStore([
        {"experiment_name": "consolidator_seam", "success": "yes", "recommendation": "the consolidator seam wires faithfulness"},
        {"experiment_name": "consolidator_seam", "success": "yes", "recommendation": "the consolidator seam wires faithfulness"},
    ])
    res = recall_at(command="touch the consolidator", learning_store=dup)
    assert len(res["lessons"]) == 1, f"same source must dedup to one, got {res['lessons']}"
    print("--- dedup ---\n  duplicate source collapses to one OK")


def test_exclude_sources_anti_repeat():
    res1 = recall_at(command="edit the consolidator seam", learning_store=_STORE)
    srcs1 = {l["source"] for l in res1["lessons"]}
    assert "learn:experiment:spine1_unify" in srcs1, "first call should surface the consolidator lesson"
    res2 = recall_at(command="edit the consolidator seam", exclude_sources=srcs1, learning_store=_STORE)
    assert all(l["source"] not in srcs1 for l in res2["lessons"]), "excluded sources must not reappear"
    print("--- anti-repeat ---\n  sources shown once are excluded next time OK")


def test_query_builder_drops_noise():
    q = _query_from("core/primitives/faithfulness.py", None)
    assert "faithfulness" in q and "primitives" in q
    assert "core" not in q.split() and "py" not in q.split(), f"generic/short tokens leaked: {q}"
    print(f"--- query builder ---\n  '{q}' (dropped core/py) OK")


def test_warm_cache_and_prune():
    import core.recall.at_action as aa
    d = tempfile.mkdtemp()
    old = (aa._CACHE_DIR, aa._CACHE_FILE, aa._SEEN_DIR)
    aa._CACHE_DIR = d
    aa._CACHE_FILE = os.path.join(d, "cache.json")
    aa._SEEN_DIR = os.path.join(d, "seen")
    try:
        n = aa.warm_cache(learning_store=_STORE)
        assert n == 3 and os.path.exists(aa._CACHE_FILE), f"warm_cache should write 3 items, got {n}"
        os.makedirs(aa._SEEN_DIR, exist_ok=True)
        oldf = os.path.join(aa._SEEN_DIR, "old.txt")
        newf = os.path.join(aa._SEEN_DIR, "new.txt")
        open(oldf, "w").close()
        open(newf, "w").close()
        os.utime(oldf, (time.time() - 10 * 86400, time.time() - 10 * 86400))  # 10 days stale
        removed = aa.prune_state(max_age_days=7)
        assert removed == 1 and not os.path.exists(oldf) and os.path.exists(newf), "prune should drop only the stale file"
        print("--- warm cache + prune ---\n  warm wrote 3 items; prune dropped the 10-day-old seen file OK")
    finally:
        aa._CACHE_DIR, aa._CACHE_FILE, aa._SEEN_DIR = old


def test_usefulness_factor():
    from core.recall.at_action import usefulness_factor
    assert abs(usefulness_factor(None) - 1.0) < 0.01, "unseen -> neutral 1.0"
    assert usefulness_factor({"useful": 3, "surfaced": 3}) > 1.2, "proven-useful -> boosted"
    assert usefulness_factor({"surfaced": 10}) < 0.7, "shown often, never useful -> noise decay"
    assert usefulness_factor({"noise": 2, "surfaced": 2}) < 0.7, "noise-voted -> demoted"
    print("--- usefulness factor ---\n  neutral / boost / noise-decay / demote OK")


def test_record_feedback_counters():
    from core.recall.at_action import record_feedback, _load_use
    from core.foundation.store import FileStore
    st = FileStore(os.path.join(tempfile.mkdtemp(), "use.json"))
    assert record_feedback("learn:experiment:x", "useful", store=st) is True
    assert record_feedback("learn:experiment:x", "useful", store=st) is True
    assert record_feedback("learn:experiment:x", "noise", store=st) is True
    use = _load_use(st, "learn:experiment:x")
    assert use.get("useful") == 2 and use.get("noise") == 1, f"counters should accumulate, got {use}"
    assert record_feedback("", "useful", store=st) is False, "empty source rejected"
    assert record_feedback("y", "bogus", store=st) is False, "bad kind rejected"
    print("--- record_feedback ---\n  votes accumulate; bad input rejected OK")


def test_usefulness_reranks_equally_relevant():
    import core.recall.at_action as aa
    items = [
        {"text": "alpha consolidator lesson", "source": "learn:experiment:A", "importance": 3, "_use": {}},
        {"text": "beta consolidator lesson", "source": "learn:experiment:B", "importance": 3,
         "_use": {"useful": 5, "surfaced": 5}},
    ]
    orig = aa._cached_items
    aa._cached_items = lambda ls: items   # both equally relevant to "consolidator"; B is proven-useful
    try:
        out = aa._lessons("consolidator", None, 2, 0.0)
        assert out and out[0]["source"] == "learn:experiment:B", \
            f"proven-useful lesson should rank first: {[o['source'] for o in out]}"
    finally:
        aa._cached_items = orig
    print("--- usefulness re-rank ---\n  proven-useful lesson outranks an equally-relevant one OK")


def test_usefulness_factor_helped():
    from core.recall.at_action import usefulness_factor
    assert usefulness_factor({"helped": 3, "surfaced": 3}) > 1.2, "proven by flips -> boosted"
    assert usefulness_factor({"helped": 2, "surfaced": 4}) > usefulness_factor({"surfaced": 4}), "helped beats no-signal"
    assert usefulness_factor({"helped": 99, "surfaced": 1}) <= 1.5, "can't farm a jackpot (capped + bounded)"
    print("--- usefulness factor (helped) ---\n  flips boost, capped, never a jackpot OK")


def test_implicit_helped_flip():
    import core.recall.at_action as aa
    from core.foundation.store import FileStore
    d = tempfile.mkdtemp()
    old = (aa._CACHE_DIR, aa._IMP_DIR, aa._OUTCOME_DIR)
    aa._CACHE_DIR, aa._IMP_DIR, aa._OUTCOME_DIR = d, os.path.join(d, "imp"), os.path.join(d, "outcome")
    st = FileStore(os.path.join(d, "use.json"))
    try:
        sid, tgt = "sess1", "p:/x/consolidator.py"
        aa.mark_impression(sid, tgt, ["learn:experiment:A", "learn:experiment:B"])
        # first-try SUCCESS (no prior FAIL) credits NOTHING -- the contrastive gate
        assert aa.resolve_outcome(sid, tgt, True, store=st) == 0, "first-try success must not credit"
        # FAIL then SUCCESS -> credit both surfaced lessons
        aa.resolve_outcome(sid, tgt, False, store=st)
        assert aa.resolve_outcome(sid, tgt, True, store=st) == 2, "FAIL->SUCCESS credits surfaced lessons"
        assert aa._load_use(st, "learn:experiment:A").get("helped") == 1
        # consume-on-credit: another FAIL->SUCCESS doesn't re-credit (impressions were consumed)
        aa.resolve_outcome(sid, tgt, False, store=st)
        assert aa.resolve_outcome(sid, tgt, True, store=st) == 0, "consumed impressions never re-credit"
    finally:
        aa._CACHE_DIR, aa._IMP_DIR, aa._OUTCOME_DIR = old
    print("--- implicit helped flip ---\n  FAIL->SUCCESS credits once; first-try + re-success credit nothing OK")


def test_render_formats_and_empties():
    res = {"lessons": [{"text": "route every source through the one consolidator seam",
                        "source": "learn:experiment:spine1_unify"}],
           "locks": [{"held_by": "cursor", "reason": "editing"}]}
    out = render(res)
    assert "[lock] cursor" in out and "[lesson]" in out and "(source: learn:experiment:spine1_unify)" in out
    assert len(out) <= 900
    assert render({"lessons": [], "locks": []}) == "", "empty result must render to ''"
    print("--- render ---\n  factual lock+lesson lines; empty -> '' OK")


def test_fail_soft_on_empty_and_bad_input():
    assert recall_at()["shown"] == 0                       # no path/command
    assert recall_at(command="", path="")["shown"] == 0
    assert recall_at(command="anything", learning_store=object())["shown"] == 0  # store with no method -> caught
    print("--- fail-soft ---\n  empty/bad input -> empty result, never raises OK")


if __name__ == "__main__":
    print("=" * 60)
    print("RECALL-AT-ACTION CHARACTERIZATION")
    print("=" * 60)
    test_relevant_command_surfaces_the_matching_lesson()
    test_show_nothing_when_irrelevant()
    test_never_pads_to_limit()
    test_dedup_by_source()
    test_exclude_sources_anti_repeat()
    test_query_builder_drops_noise()
    test_warm_cache_and_prune()
    test_usefulness_factor()
    test_record_feedback_counters()
    test_usefulness_reranks_equally_relevant()
    test_usefulness_factor_helped()
    test_implicit_helped_flip()
    test_render_formats_and_empties()
    test_fail_soft_on_empty_and_bad_input()
    print("\n" + "=" * 60)
    print("ALL RECALL-AT-ACTION TESTS PASSED")
    print("=" * 60)
