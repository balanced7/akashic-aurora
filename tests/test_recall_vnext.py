"""Recall vNext (docs/recall-vnext-2026-07.md) -- the four closed loops.

Pins: (1) CURATION -- bench fires only on exposure+time+zero-credit, unbench restores on any credit,
graduated lessons are out of scope, benched lessons leave the surface projection; (2) PRECISION --
the 'Use when' trigger clause is parsed and DOMINATES matching, mined credited-flip targets extend
the trigger vocabulary, the show-nothing floor defaults ON (calibrated), self-echo suppression hides
an author's fresh lesson from the author only; (3) CREDIT -- 'engaged' is a countable kind, a full
pull records it; (4) the wrap draft carries the RECALL REVIEW + corpus-gap sections.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

from core.recall import at_action as aa
from core.recall import curator as cu


# ---------- fakes ------------------------------------------------------------------------------

class FakeLearningStore:
    """Duck-typed learning store: records + the benched/graduated stamp surface."""
    def __init__(self, recs):
        self.recs = {r["experiment_name"]: dict(r) for r in recs}
        self.benched, self.unbenched = [], []

    def load_all_learnings_from_store(self):
        return [dict(r) for r in self.recs.values()]

    def mark_benched(self, name, reason="", *, undo=False):
        if name not in self.recs:
            return False
        if undo:
            self.recs[name]["benched"] = ""
            self.unbenched.append(name)
        else:
            self.recs[name]["benched"] = datetime.utcnow().isoformat()
            self.benched.append(name)
        return True

    def _load_experiment(self, exp_id):
        return dict(self.recs.get(exp_id) or {})


class FakeStore:
    """Minimal Store for the use-counters (get/set/exists/keys)."""
    def __init__(self, d=None):
        self.d = dict(d or {})

    def get(self, k):
        return self.d.get(k)

    def set(self, k, v):
        self.d[k] = v

    def exists(self, k):
        return k in self.d

    def keys(self, pattern):
        prefix = pattern.rstrip("*")
        return [k for k in self.d if k.startswith(prefix)]

    def delete(self, k):
        self.d.pop(k, None)


def _rec(name, rec="", ts_days_ago=30.0, agent="claude", success="yes", **kw):
    return {"experiment_name": name, "recommendation": rec or f"Use when testing {name}: do the thing",
            "timestamp": (datetime.now() - timedelta(days=ts_days_ago)).isoformat(),
            "agent_id": agent, "success": success, **kw}


def _use(store, name, **counts):
    store.set(f"recall:use:learn:experiment:{name}", json.dumps(counts))


# ---------- 1. curation loop -------------------------------------------------------------------

def _report(ls, st, **kw):
    return cu.curation_report(store=st, learning_store=ls, **kw)


def test_bench_needs_exposure_and_age_and_zero_credit():
    ls = FakeLearningStore([_rec("old_cold", ts_days_ago=30), _rec("young_cold", ts_days_ago=2),
                            _rec("old_hot", ts_days_ago=30), _rec("old_quiet", ts_days_ago=30)])
    st = FakeStore()
    _use(st, "old_cold", surfaced=15)                    # exposed + old + no credit -> bench
    _use(st, "young_cold", surfaced=15)                  # exposed but YOUNG -> keep
    _use(st, "old_hot", surfaced=15, helped=1)           # credited -> keep
    _use(st, "old_quiet", surfaced=3)                    # under-exposed -> keep
    rep = _report(ls, st)
    assert [r["name"] for r in rep["bench"]] == ["old_cold"]
    assert rep["surface_active"] == 4 and rep["corpus"] == 4


def test_engaged_counts_as_credit_and_protects():
    ls = FakeLearningStore([_rec("pulled_once", ts_days_ago=30)])
    st = FakeStore()
    _use(st, "pulled_once", surfaced=20, engaged=1)      # someone pulled the full record
    assert _report(ls, st)["bench"] == []


def test_missing_timestamp_is_never_benched():
    ls = FakeLearningStore([{"experiment_name": "undated", "recommendation": "x",
                             "timestamp": "", "agent_id": "claude", "success": "yes"}])
    st = FakeStore()
    _use(st, "undated", surfaced=50)
    assert _report(ls, st)["bench"] == []                # only bench what is PROVABLY old


def test_unbench_on_new_credit_and_graduated_out_of_scope():
    ls = FakeLearningStore([
        _rec("benched_now_credited", ts_days_ago=30, benched="2026-07-01T00:00:00"),
        _rec("graduated_cold", ts_days_ago=30, graduated="2026-07-01T00:00:00"),
    ])
    st = FakeStore()
    _use(st, "benched_now_credited", surfaced=20, useful=1)
    _use(st, "graduated_cold", surfaced=50)              # graduation outranks benching
    rep = _report(ls, st)
    assert [r["name"] for r in rep["unbench"]] == ["benched_now_credited"]
    assert rep["bench"] == []
    out = cu.apply_curation(rep, store=st, learning_store=ls)
    assert out["unbenched"] == ["benched_now_credited"] and ls.recs["benched_now_credited"]["benched"] == ""


def test_apply_stamps_bench_and_projection_drops_benched():
    ls = FakeLearningStore([_rec("cold", ts_days_ago=30), _rec("warm", ts_days_ago=30)])
    st = FakeStore()
    _use(st, "cold", surfaced=15)
    _use(st, "warm", surfaced=15, helped=2)
    out = cu.apply_curation(_report(ls, st), store=st, learning_store=ls)
    assert out["benched"] == ["cold"]
    items = aa._project_items(ls.load_all_learnings_from_store())
    assert [i["source"] for i in items] == ["learn:experiment:warm"]   # benched left the surface


# ---------- 2. precision loop ------------------------------------------------------------------

def test_parse_trigger_extracts_the_use_when_clause():
    assert aa._parse_trigger("Use when a hook matcher changes, before editing: check X") == \
        "a hook matcher changes, before editing"
    assert aa._parse_trigger("use  WHEN the bus wedges. Then restart.") == "the bus wedges"
    assert aa._parse_trigger("Always frobnicate first.") == ""
    assert aa._parse_trigger("") == ""


def test_trigger_dominates_prose_matching():
    items = [
        {"text": "Use when editing pretooluse hooks: pin the matcher config first",
         "trigger": "editing pretooluse hooks", "source": "learn:experiment:hooky",
         "importance": 4, "timestamp": datetime.now().isoformat()},
        {"text": "refactoring continue working systematic pattern hooks mention",
         "trigger": "", "source": "learn:experiment:prosey",
         "importance": 4, "timestamp": datetime.now().isoformat()},
    ]
    fn = aa._trigger_aware_relevance({i["text"]: i for i in items})
    q = "pretooluse hooks editing"
    assert fn(items[0]["text"], q) > fn(items[1]["text"], q)


def test_mined_trigger_terms_from_credited_flips(monkeypatch):
    import core.events.event_log as el

    class _Log:
        def recent(self, limit=2000):
            return [
                {"kind": "flip", "detail": {"target": "c:py scripts/bifrost_wake.py --agent claude",
                                            "credited": 1, "sources": ["learn:experiment:wakey"]}},
                {"kind": "flip", "detail": {"target": "c:py probe.py", "credited": 0,
                                            "sources": ["learn:experiment:uncredited"]}},
            ]
    monkeypatch.setattr(el, "get_event_log", lambda *a, **k: _Log())
    items = [{"text": "t", "source": "learn:experiment:wakey"},
             {"text": "u", "source": "learn:experiment:uncredited"}]
    out = aa._with_mined_triggers(items)
    assert {"bifrost", "wake"} <= set(out[0]["trigger_terms"])
    assert "agent" not in out[0]["trigger_terms"]   # domain-generic: STOP'd from mined vocabulary
    assert "trigger_terms" not in out[1]           # uncredited flips teach nothing (they are gaps)


def test_damped_overlap_idf_and_lone_common_hit():
    # a lone CORPUS-COMMON hit (low IDF weight) is damped: tiny mass, then halved
    w = {"deploy": 0.2}
    got = aa._damped_overlap("we deploy the frobnicator", "deploy nightly artifacts safely", w)
    assert got == round(0.2 / 3.2 * 0.5, 10) or abs(got - (0.2 / 3.2) * 0.5) < 1e-9
    # a lone RARE hit is the designed path->lesson match: NOT damped
    assert aa._damped_overlap("frobnicate the zorbulator", "zorbulator tune") == 0.5
    # multiple real hits -> full weighted fraction
    assert aa._damped_overlap("signal half and label half of a dataset",
                              "correlation dataset signal label") >= 0.5
    # a query with zero discriminative mass scores 0 against everything
    assert aa._damped_overlap("anything at all", "common words only", {"common": 0.0, "words": 0.0,
                                                                       "only": 0.0}) == 0.0


def test_floor_default_is_on_and_env_tunable(monkeypatch):
    monkeypatch.delenv("AKASHIC_RECALL_FLOOR", raising=False)
    assert aa._floor_default() == 0.20
    monkeypatch.setenv("AKASHIC_RECALL_FLOOR", "0.25")
    assert aa._floor_default() == 0.25


def test_self_echo_suppressed_for_author_only_then_expires():
    # PRODUCTION-SHAPED timestamps: records stamp utcnow()-naive (naive==UTC per timeutil).
    # A local-now() fixture masked the tz bug the live flight test caught -- never again.
    from datetime import datetime as dt
    fresh = {"agent_id": "claude", "timestamp": dt.utcnow().isoformat()}
    old = {"agent_id": "claude",
           "timestamp": (dt.utcnow() - timedelta(hours=3)).isoformat()}
    now = time.time()
    assert aa._self_echo(fresh, "claude", now) is True
    assert aa._self_echo(fresh, "deepseek", now) is False   # other agents still see it
    assert aa._self_echo(old, "claude", now) is False       # window passed


def test_recall_at_floor_gates_weak_matches():
    recs = [_rec("weak", rec="Use when frobnicating the zorbulator: care", ts_days_ago=1)]
    ls = FakeLearningStore(recs)
    # one weak token overlap ('scripts') out of many query tokens -> below the default floor
    res = aa.recall_at(command="cd scripts && run the long pipeline now", learning_store=ls)
    assert res["lessons"] == []
    # a genuine trigger hit clears it
    res2 = aa.recall_at(command="frobnicating the zorbulator carefully", learning_store=ls)
    assert [l["source"] for l in res2["lessons"]] == ["learn:experiment:weak"]


# ---------- 3. credit loop ---------------------------------------------------------------------

def test_engaged_is_a_recordable_kind(monkeypatch):
    st = FakeStore()
    assert aa.record_feedback("learn:experiment:x", "engaged", store=st) is True
    assert json.loads(st.get("recall:use:learn:experiment:x"))["engaged"] == 1
    assert aa.record_feedback("learn:experiment:x", "bogus", store=st) is False


def test_full_record_records_engagement(monkeypatch):
    ls = FakeLearningStore([_rec("deep_dive")])
    seen = []
    monkeypatch.setattr(aa, "record_feedback", lambda src, kind, **kw: seen.append((src, kind)) or True)
    rec = aa.full_record("learn:experiment:deep_dive", learning_store=ls)
    assert rec.get("experiment_name") == "deep_dive"
    assert seen == [("learn:experiment:deep_dive", "engaged")]
    aa.full_record("learn:experiment:missing", learning_store=ls)
    assert len(seen) == 1                                  # a miss engages nothing


# ---------- 4. wrap surfaces -------------------------------------------------------------------

def test_wrap_draft_has_recall_review_and_gap_sections():
    sys.path.insert(0, os.getenv("AI_SETUP", "E:\\AI-Setup"))
    import agent_cli
    flips = [{"t": "c:py fixed_thing.py", "credited": 0}]
    injections = [{"alt": "action", "s": ["learn:experiment:hit", "learn:experiment:miss"], "chars": 200},
                  {"alt": "plan", "s": ["learn:experiment:hit"], "chars": 100}]
    draft = agent_cli.build_session_draft([], [], [], flips=flips, injections=injections)
    assert "Corpus gaps (1 uncredited flip target(s)" in draft
    assert "Recall review (2 lesson(s) surfaced this session" in draft
    assert "2x hit" in draft
    assert "recall-feedback --source learn:experiment:hit" in draft
    assert "--noise" in draft
