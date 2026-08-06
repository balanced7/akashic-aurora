"""
T199 -- friction v2: who answers, and does presence predict it. RED before impl.

Sol's collaboration-first write-up asks for friction to be MEASURED, listing commands
per task, time to first useful output, operator interventions, recovery time. This slice
does NOT claim those four. It builds the two the durable evidence can honestly support
today, and the blind list keeps naming the rest as missing rather than quietly
redefining the ask:

  by_peer         per-peer episode counts + dead rate + median settle. "deepseek: 2
                  answered / 10 dead" and "kimi: 0 of 4" are different problems from
                  one fleet-wide 76.5%, and they have different fixes.
  presence_effect of asks sent to an ATTENDED peer, what fraction were answered -- and
                  the same for UNATTENDED. THE QUESTION THE WHOLE T197 ARC IS FOR. The
                  T197 pins said out loud that a partition defined only over failures
                  "cannot answer 'do attended peers actually answer more often?'", and
                  recorded peer_at_ask on settled events precisely so this could exist.

WHY IT IS NOT JUST A NICER TABLE. T197 shipped autolaunch on the reasoning that absent
peers cause dead asks. That is a HYPOTHESIS, and 26 of the 26 historical deaths carry no
peer observation, so it is currently untestable from the record. presence_effect is the
instrument that can eventually falsify it: if attended peers die at the same rate as
unattended ones, then launching peers was the wrong fix and the defect is downstream in
the consumer. Building the thing that can prove me wrong is the point.

RATES OVER ZERO ARE None, NEVER 0.0 -- the house law, and it bites hard here: early on,
every cell has a denominator of 0 or 1, and a 0.0 answer-rate rendered against n=1 would
read as "attended peers never answer" on a single data point.

Run: py -m pytest tests/test_t199_friction_v2.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import friction  # noqa: E402


def _ev(kind, ask_id, peer, *, at_ask=None, at_death=None, created=1000.0,
        at="2026-08-06T00:00:10Z"):
    d = {"to": peer, "kind": "request", "created": created}
    if kind == "expectation_dead":
        d["attempts"] = 3
        if at_death is not None:
            d["peer_at_death"] = at_death
    else:
        d["attempt"] = 0
    if at_ask is not None:
        d["peer_at_ask"] = at_ask
    return {"kind": kind, "at": at, "refs": [ask_id], "detail": d}


def _answered(ask_id, peer, **kw):
    return _ev("expectation_settled_answered", ask_id, peer, **kw)


def _dead(ask_id, peer, **kw):
    return _ev("expectation_dead", ask_id, peer, **kw)


# --------------------------------------------------------------------------------------
# by_peer -- one fleet number hides which peer is actually broken.
# --------------------------------------------------------------------------------------

def test_by_peer_splits_the_fleet_number():
    events = [_answered("a1", "deepseek"), _answered("a2", "deepseek"),
              _dead("a3", "deepseek"), _dead("a4", "kimi"), _dead("a5", "kimi")]
    by = friction.fold(events, {}, now=2000.0)["agg"]["by_peer"]
    assert by["deepseek"]["n_answered"] == 2 and by["deepseek"]["n_dead"] == 1
    assert by["kimi"]["n_answered"] == 0 and by["kimi"]["n_dead"] == 2
    assert by["kimi"]["dead_rate"] == 1.0
    assert abs(by["deepseek"]["dead_rate"] - 1 / 3) < 1e-9


def test_by_peer_counts_open_episodes_too():
    """An ask still in flight is not evidence of success OR failure, but a peer with
    nine open asks and zero closed is a distinct and visible situation."""
    open_recs = {"o1": {"to": "sol", "created": 1000.0, "attempt": 0}}
    by = friction.fold([], open_recs, now=2000.0)["agg"]["by_peer"]
    assert by["sol"]["n_open"] == 1 and by["sol"]["n_closed"] == 0
    assert by["sol"]["dead_rate"] is None, "a rate over zero closed is not a number"


def test_by_peer_is_sorted_by_pain_not_alphabet():
    """The reader's job is to put the broken peer first. Ordering by dead count then
    name keeps it stable AND useful; alphabetical would bury the failure."""
    events = [_dead("a1", "zeta"), _dead("a2", "zeta"), _dead("a3", "zeta"),
              _answered("a4", "alpha")]
    order = list(friction.fold(events, {}, now=2000.0)["agg"]["by_peer"].keys())
    assert order[0] == "zeta"


def test_unknown_peer_never_becomes_a_bucket_named_none():
    """A malformed event without `to` must not create a peer literally called None."""
    ev = _answered("a1", None)
    by = friction.fold([ev], {}, now=2000.0)["agg"]["by_peer"]
    assert None not in by and "None" not in by


# --------------------------------------------------------------------------------------
# presence_effect -- the instrument that can falsify T197's own premise.
# --------------------------------------------------------------------------------------

def test_presence_effect_answers_the_arcs_question():
    events = [_answered("a1", "deepseek", at_ask="ATTENDED"),
              _answered("a2", "deepseek", at_ask="ATTENDED"),
              _dead("a3", "deepseek", at_ask="ATTENDED", at_death="ATTENDED"),
              _dead("a4", "kimi", at_ask="UNATTENDED", at_death="UNATTENDED"),
              _dead("a5", "kimi", at_ask="UNATTENDED", at_death="UNATTENDED")]
    pe = friction.fold(events, {}, now=2000.0)["agg"]["presence_effect"]
    assert pe["ATTENDED"]["n"] == 3 and pe["ATTENDED"]["n_answered"] == 2
    assert abs(pe["ATTENDED"]["answer_rate"] - 2 / 3) < 1e-9
    assert pe["UNATTENDED"]["n"] == 2 and pe["UNATTENDED"]["n_answered"] == 0
    assert pe["UNATTENDED"]["answer_rate"] == 0.0


def test_a_rate_over_zero_asks_is_none_not_zero():
    """The law that bites hardest here: with no ATTENDED episodes yet, 0.0 would read
    as 'attended peers never answer' -- a fabricated finding from an empty cell."""
    pe = friction.fold([_dead("a1", "kimi", at_ask="UNATTENDED", at_death="UNATTENDED")],
                       {}, now=2000.0)["agg"]["presence_effect"]
    assert pe["ATTENDED"]["n"] == 0
    assert pe["ATTENDED"]["answer_rate"] is None


def test_unobserved_episodes_are_excluded_not_bucketed_as_unattended():
    """The 26 historical deaths carry no peer observation. Counting them as UNATTENDED
    would manufacture exactly the correlation this instrument exists to test -- the
    single most tempting error available here, so it is pinned."""
    events = [_dead(f"h{i}", "deepseek") for i in range(26)]
    pe = friction.fold(events, {}, now=2000.0)["agg"]["presence_effect"]
    assert pe["UNATTENDED"]["n"] == 0 and pe["ATTENDED"]["n"] == 0
    assert pe["n_unobserved"] == 26, "excluded, but COUNTED -- never silently dropped"


def test_presence_effect_ignores_echo_episodes():
    """A T076c echo settled from ledger state, with no message anywhere. It says
    nothing about whether a present peer answers mail, so it must not inflate either
    numerator or denominator."""
    events = [{"kind": "expectation_settled_done_task", "at": "2026-08-06T00:00:10Z",
               "refs": ["e1"], "detail": {"to": "deepseek", "created": 1000.0,
                                          "peer_at_ask": "ATTENDED"}}]
    pe = friction.fold(events, {}, now=2000.0)["agg"]["presence_effect"]
    assert pe["ATTENDED"]["n"] == 0


def test_totals_still_reconcile_with_v1():
    """v2 adds views, never changes the headline. A breakdown that disagrees with the
    total it breaks down is worse than no breakdown."""
    events = [_answered("a1", "deepseek", at_ask="ATTENDED"),
              _dead("a2", "kimi", at_ask="UNATTENDED", at_death="UNATTENDED"),
              _dead("a3", "kimi")]
    agg = friction.fold(events, {}, now=2000.0)["agg"]
    assert agg["n_answered"] == 1 and agg["n_dead"] == 2 and agg["n_closed"] == 3
    assert sum(p["n_closed"] for p in agg["by_peer"].values()) == agg["n_closed"]
    observed = sum(agg["presence_effect"][k]["n"] for k in ("ATTENDED", "UNATTENDED"))
    assert observed + agg["presence_effect"]["n_unobserved"] == agg["n_closed"] - agg["n_echo"]


def test_blind_names_the_metrics_still_missing():
    """Sol asked for four metrics; this slice builds two different ones. Saying so is
    the difference between an honest partial and a quietly redefined ask."""
    blind = " ".join(friction.fold([], {}, now=1.0)["blind"]).lower()
    for term in ("commands per task", "operator intervention", "recovery time"):
        assert term in blind, f"unbuilt metric not confessed: {term}"


def test_presence_effect_is_correlational_and_says_so():
    """It cannot license 'launching peers causes answers' -- the same conductor who
    launches a peer also asks better-formed questions to peers worth launching. The
    caveat ships WITH the number, not in a doc nobody reads."""
    blind = " ".join(friction.fold([], {}, now=1.0)["blind"]).lower()
    assert "correlation" in blind or "causal" in blind
