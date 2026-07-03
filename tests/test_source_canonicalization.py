"""S2a: one counter key per lesson. Votes cast with bare slugs must land on (and merge
into) the lesson's canonical learn:experiment:* counter -- the first triage run found
parallel counters that never joined (127 tracked vs 122 corpus)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.at_action import (canonicalize_source, merge_use_counters,
                                    prune_ghost_counters, record_feedback)


class _FakeLearning:
    def __init__(self, names):
        self._names = names

    def load_all_learnings_from_store(self):
        return [{"experiment_name": n} for n in self._names]


class _FakeStore:
    def __init__(self, data=None):
        self.d = dict(data or {})

    def keys(self, pattern):
        prefix = pattern.rstrip("*")
        return [k for k in self.d if k.startswith(prefix)]

    def get(self, k):
        return self.d.get(k)

    def set(self, k, v):
        self.d[k] = v

    def delete(self, k):
        self.d.pop(k, None)


_LS = _FakeLearning(["session_hooks_need_matcher", "thinking_model_empty_reply"])


def test_bare_known_slug_canonicalizes():
    assert canonicalize_source("session_hooks_need_matcher", learning_store=_LS) == \
        "learn:experiment:session_hooks_need_matcher"


def test_namespaced_and_unknown_pass_through():
    assert canonicalize_source("learn:experiment:x", learning_store=_LS) == "learn:experiment:x"
    assert canonicalize_source("ADR_0701010114_6136", learning_store=_LS) == "ADR_0701010114_6136"
    assert canonicalize_source("mem:decision:y", learning_store=_LS) == "mem:decision:y"
    assert canonicalize_source("", learning_store=_LS) == ""


def test_merge_folds_bare_into_canonical_and_removes_bare():
    st = _FakeStore({
        "recall:use:session_hooks_need_matcher": json.dumps({"useful": 1}),
        "recall:use:learn:experiment:session_hooks_need_matcher": json.dumps({"surfaced": 4, "helped": 1}),
        "recall:use:learn:experiment:thinking_model_empty_reply": json.dumps({"surfaced": 2}),
        "recall:use:ADR_0701010114_6136": json.dumps({"useful": 1}),   # note id: untouched
    })
    merged = merge_use_counters(store=st, learning_store=_LS)
    assert merged == 1
    canon = json.loads(st.d["recall:use:learn:experiment:session_hooks_need_matcher"])
    assert canon == {"surfaced": 4, "helped": 1, "useful": 1}
    assert "recall:use:session_hooks_need_matcher" not in st.d, "bare key folded away"
    assert "recall:use:ADR_0701010114_6136" in st.d, "non-lesson sources untouched"
    assert merge_use_counters(store=st, learning_store=_LS) == 0, "idempotent re-run"


def test_record_feedback_lands_on_canonical_key(monkeypatch):
    import core.recall.at_action as aa
    st = _FakeStore()
    monkeypatch.setattr(aa, "canonicalize_source",
                        lambda s, **k: canonicalize_source(s, learning_store=_LS))
    assert record_feedback("session_hooks_need_matcher", "useful", store=st)
    assert "recall:use:learn:experiment:session_hooks_need_matcher" in st.d
    assert "recall:use:session_hooks_need_matcher" not in st.d


# --------------------------------------------------------- ghost counters (retired lessons)
def test_prune_drops_zero_credit_ghost_keeps_credited_and_live():
    """A ghost = a learn:experiment:* counter whose lesson is gone. Zero-credit ghosts are
    bookkeeping debt (deleted); a ghost WITH credit is earned signal outliving its lesson
    (kept for S2 to fold into the successor). Live-lesson and non-lesson keys are untouched."""
    st = _FakeStore({
        "recall:use:learn:experiment:session_hooks_need_matcher": json.dumps({"surfaced": 9, "useful": 1}),
        "recall:use:learn:experiment:gone_no_credit": json.dumps({"surfaced": 4}),          # zero-credit ghost
        "recall:use:learn:experiment:gone_with_credit": json.dumps({"surfaced": 3, "helped": 1}),  # credited ghost
        "recall:use:ADR_0701010114_6136": json.dumps({"useful": 1}),                        # note id: not a lesson
    })
    res = prune_ghost_counters(store=st, learning_store=_LS)
    assert res["pruned"] == ["learn:experiment:gone_no_credit"]
    assert res["kept_credited"] == ["learn:experiment:gone_with_credit"]
    assert "recall:use:learn:experiment:gone_no_credit" not in st.d, "zero-credit ghost deleted"
    assert "recall:use:learn:experiment:gone_with_credit" in st.d, "credited ghost kept for adjudication"
    assert "recall:use:learn:experiment:session_hooks_need_matcher" in st.d, "live lesson untouched"
    assert "recall:use:ADR_0701010114_6136" in st.d, "non-lesson source untouched"
    assert prune_ghost_counters(store=st, learning_store=_LS)["pruned"] == [], "idempotent re-run"


def test_prune_is_noop_on_empty_corpus():
    """A broken/empty corpus read must NOT classify every counter as a ghost and wipe the store."""
    st = _FakeStore({"recall:use:learn:experiment:real": json.dumps({"surfaced": 5})})
    res = prune_ghost_counters(store=st, learning_store=_FakeLearning([]))
    assert res["pruned"] == [] and "recall:use:learn:experiment:real" in st.d
