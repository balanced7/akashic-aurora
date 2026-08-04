"""PRE-REGISTERED ACCEPTANCE (T165) -- Season 1 scoring, as a pure function instead of a table.

The scoring rules exist today ONLY as a markdown table in
docs/library/report/20260804_game-arc-season1-mechanics-opus5_b864f1.md section 1.6. Nothing
executes them. That is the same shape as every other defect this watch turned up -- a rule that
lives in prose drifts from whatever eventually gets built, and nobody can tell when it has,
because there is nothing to run.

It also blocks the W2 queue item. The four AIxCC-derived refinements (uptime as a scored axis, a
graduated accuracy penalty replacing the flat -2, dedup costing time-decay rather than a hard
zero, value-weighted points) cannot be RULED ON while both the old and the new rules are prose.
So both ship as DATA: policy v1_doc reproduces the committed table exactly, policy v2_aixcc
carries the proposals, and the operator rules on a measured diff over the same inputs.

WHAT IS PINNED HERE IS MOSTLY *INVARIANTS*, NOT WEIGHTS. Weights are Daniil's to set and are
deliberately data, changeable without touching code or tests. The invariants below are the ones
where getting it wrong corrupts the season's evidence rather than merely mis-ranking a player.

  S1  first-finder is ordered by BUS STREAM ID, never by the player's submitted_at. Player clocks
      are not trustworthy and the doc calls the field advisory; ordering a competition by an
      attacker-supplied timestamp decides the winner by whoever lies best.
  S2  NO RECEIPTS, NO SCORE -- a claim with zero resolvable evidence is UNSCORED, which is a
      third state and not a zero. Zero says "we weighed it and it was worth nothing"; unscored
      says "this was never evidence". Collapsing them is how an unfalsifiable claim earns a rank.
  S3  SCORE IS EVIDENCE, NEVER A KEY (Daniil, L4). Structural: nothing in the scorer may import
      or touch the trust/ACL layer, so a score can never become an access decision by accident.
  S4  an honest LOW-CONFIDENCE claim that is refuted floors at 0. Punishing it teaches players to
      overstate, which is the one behaviour a bounty system cannot afford to train.
  S5  ALREADY-KNOWN is 0 and never negative -- rediscovery is honest work.
  S6  VERIFICATION PAYS, or nobody verifies and the design collapses to unchecked volume.
  S7  the policy is SWAPPABLE DATA -- both rule sets score the same input, so a change of rules
      is a config decision with a visible diff, never a code edit
  S8  v1_doc REPRODUCES THE COMMITTED TABLE exactly, so the design document stays executable and
      a drift between doc and code becomes a test failure instead of an argument
  S9  DETERMINISM -- same inputs, same score, in any submission order. A scoreboard that depends
      on evaluation order cannot be audited or replayed.

Run: py -m pytest tests/test_t165_season_scoring.py -q
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _s():
    import importlib
    from core.season import scoring
    return importlib.reload(scoring)


def _claim(**kw):
    base = dict(player="p1", dedupe_key="k1", claim_class="needs-door", outcome="confirmed",
                confidence="high", stream_id="1785850000000-0",
                evidence=["core/comm/bus.py:120 no caller"])
    base.update(kw)
    return base


# --------------------------------------------------------------------------- S1

def test_s1_first_finder_is_ordered_by_stream_id_not_player_clock():
    s = _s()
    early_stream_late_clock = _claim(player="honest", stream_id="1785850000000-0",
                                     submitted_at="2099-01-01T00:00:00Z")
    late_stream_early_clock = _claim(player="liar", stream_id="1785850000999-0",
                                     submitted_at="1970-01-01T00:00:00Z")
    res = s.score_round([late_stream_early_clock, early_stream_late_clock])
    winner = [r for r in res["claims"] if r["first_finder"]]
    assert len(winner) == 1
    assert winner[0]["player"] == "honest", (
        "first-finder was decided by a player-supplied timestamp -- the competition is then won "
        "by whoever lies best about their clock")


# --------------------------------------------------------------------------- S2

def test_s2_no_receipts_no_score_is_a_third_state():
    s = _s()
    res = s.score_round([_claim(evidence=[])])
    r = res["claims"][0]
    assert r["scored"] is False, "a claim with no evidence was scored"
    assert r["points"] == 0
    assert r["reason"] and "evidence" in r["reason"].lower()
    assert res["totals"].get("p1", 0) == 0


# --------------------------------------------------------------------------- S3

def test_s3_score_is_evidence_never_a_key():
    """Structural: the scorer must not be able to reach the authority layer at all."""
    import ast
    src = open(os.path.join(ROOT, "core", "season", "scoring.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add(n.module or "")
    forbidden = [m for m in imported if "trust" in m or "acl" in m or "toolbox" in m]
    assert not forbidden, (
        f"the scorer imports the authority layer ({forbidden}) -- a score must never be readable "
        f"as an access decision (Daniil, L4: score is evidence, never a key)")


# --------------------------------------------------------------------------- S4 / S5

def test_s4_an_honest_low_confidence_miss_is_floored_at_zero():
    s = _s()
    high = s.score_round([_claim(outcome="refuted", confidence="high")])["claims"][0]
    low = s.score_round([_claim(outcome="refuted", confidence="low")])["claims"][0]
    assert low["points"] == 0, "an honest low-confidence report was punished"
    assert high["points"] < 0, "a confident wrong claim cost nothing"


def test_s5_already_known_is_zero_never_negative():
    s = _s()
    r = s.score_round([_claim(outcome="already-known")])["claims"][0]
    assert r["points"] == 0, "rediscovery was punished; it is honest work"


# --------------------------------------------------------------------------- S6

def test_s6_verification_pays():
    s = _s()
    res = s.score_round([], verifications=[
        {"player": "v1", "verdict": "confirmed", "upheld": False},
        {"player": "v1", "verdict": "refuted", "upheld": True},
    ])
    assert res["totals"]["v1"] > 0, (
        "verification scored nothing -- if verifying does not pay, nobody verifies and the "
        "season collapses to unchecked volume")


# --------------------------------------------------------------------------- S7

def test_s7_the_policy_is_swappable_data():
    s = _s()
    assert set(s.POLICIES) >= {"v1_doc", "v2_aixcc"}
    c = [_claim(outcome="refuted", confidence="high")]
    a = s.score_round(c, policy="v1_doc")
    b = s.score_round(c, policy="v2_aixcc")
    assert a["policy"] == "v1_doc" and b["policy"] == "v2_aixcc"
    assert isinstance(a["totals"], dict) and isinstance(b["totals"], dict)

    with pytest.raises(ValueError):
        s.score_round(c, policy="not_a_policy")


# --------------------------------------------------------------------------- S8

def test_s8_v1_reproduces_the_committed_table():
    """The design doc's section 1.6, executable. Drift becomes a test failure, not an argument."""
    s = _s()
    table = {"false-positive": 5, "structural": 4, "needs-door": 3,
             "needs-caller": 2, "dead": 1, "new-blind-spot": 6}
    for cls, mult in table.items():
        r = s.score_round([_claim(claim_class=cls)], policy="v1_doc")["claims"][0]
        assert r["points"] == mult, (
            f"v1_doc scores {cls} as {r['points']}, the committed table says {mult}")

    ref = s.score_round([_claim(outcome="refuted", confidence="high")], policy="v1_doc")
    assert ref["claims"][0]["points"] == -2, "the doc's flat refuted penalty is -2"
    unv = s.score_round([_claim(outcome="unverifiable")], policy="v1_doc")
    assert unv["claims"][0]["points"] == -1, "the doc's unverifiable penalty is -1"


# --------------------------------------------------------------------------- S9

def test_s9_scoring_is_deterministic_and_order_independent():
    s = _s()
    claims = [
        _claim(player="a", dedupe_key="k1", stream_id="1785850000001-0"),
        _claim(player="b", dedupe_key="k1", stream_id="1785850000002-0"),
        _claim(player="c", dedupe_key="k2", stream_id="1785850000003-0",
               claim_class="structural"),
    ]
    first = s.score_round(claims)["totals"]
    again = s.score_round(list(reversed(claims)))["totals"]
    assert first == again, (
        f"scoring depends on submission order -- the board cannot be replayed or audited: "
        f"{first} vs {again}")
