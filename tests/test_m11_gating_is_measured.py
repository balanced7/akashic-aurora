"""PRE-REGISTERED ACCEPTANCE -- M11 must measure gate ADHERENCE, not doc mentions.

deepseek's verdict, verbatim: "M11: 17% is noise -- self-report, same trap M3 had. The scorecard
regex-matches docs/...md in commit messages. A typo fix mentioning docs/ARCHITECTURE.md counts as
gated. A full-fence slice whose message says only 'RB-99 landed' does not. This measures doc
mentions, not protocol adherence. check_reconciliation_gate.py already runs at ship time and
knows which commits actually passed. Add --audit and read that number. Until then, 17% means
nothing. Target it upward and you get more doc paths in messages, not more gated slices. Goodhart."

Both halves of that are right, and the second is the sharper one. The DENOMINATOR is also wrong:
the gate only applies to slices touching TRUST/COORDINATION SUBSTRATE (PROTECTED_PREFIXES). Most
commits never needed a gate at all, so "% of all commits citing a spec" is meaningless in both
directions. The honest question is: OF THE SLICES THAT NEEDED A GATE, HOW MANY HAD ONE.

The audit must REPLAY THE GATE'S OWN DECISION, never a lookalike regex. A second implementation
would drift from the live gate and we would be measuring a copy -- the failure this whole arc has
been about. So the decision moves into one pure function that ship-time and audit-time share.

  P1  decide() is pure and shared -- one predicate, so gate and audit cannot disagree
  P2  a non-substrate commit is NOT_APPLICABLE, not a pass and not a failure (the denominator)
  P3  a substrate commit citing a real reconciliation artifact PASSES
  P4  a substrate commit citing a doc with NO reconciliation marker FAILS -- a mention is not a gate
  P5  the [ungated: reason] hatch is a deliberate, counted exception, not a silent pass

Run: py -m pytest tests/test_m11_gating_is_measured.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scripts", "checkers"))


def _spec(tmp_path, name="docs/spec.md", body="GATE: reconciled by claude+deepseek"):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return name.replace(os.sep, "/")


def test_p1_decide_is_pure_and_shared():
    import check_reconciliation_gate as g
    assert hasattr(g, "decide"), (
        "no pure decide() -- an audit would have to reimplement the gate's predicate, and a "
        "second implementation drifts from the live gate. Measuring a copy is the disease.")


def test_p2_a_non_substrate_commit_is_not_in_the_denominator(tmp_path):
    import check_reconciliation_gate as g
    v = g.decide("fix a typo in docs/ARCHITECTURE.md", ["README.md"], root=str(tmp_path))
    assert v["status"] == "NOT_APPLICABLE", (
        "a commit touching no substrate was scored -- most commits never needed a gate, so "
        "counting them makes the rate meaningless in both directions")


def test_p3_a_substrate_commit_citing_a_real_artifact_passes(tmp_path):
    import check_reconciliation_gate as g
    rel = _spec(tmp_path)
    v = g.decide(f"bus change per {rel}", ["core/comm/bus.py"], root=str(tmp_path))
    assert v["status"] == "PASS", v


def test_p4_a_doc_mention_is_not_a_gate(tmp_path):
    """deepseek's exact example: a message naming a .md that carries no reconciliation
    record. The old scorecard counted this as gated."""
    import check_reconciliation_gate as g
    rel = _spec(tmp_path, "docs/ARCHITECTURE.md", body="just a map, no record here")
    v = g.decide(f"tweak per {rel}", ["core/comm/bus.py"], root=str(tmp_path))
    assert v["status"] == "FAIL", (
        "citing a doc with no reconciliation/GATE marker counted as gated -- that is the "
        "doc-mention trap, and targeting it upward yields more doc paths, not more gates")


def test_p5_the_hatch_is_a_counted_exception(tmp_path, monkeypatch):
    import check_reconciliation_gate as g
    monkeypatch.setenv("AKASHIC_GATE_NO_CEILING", "1")
    v = g.decide("emergency [ungated: prod down, wrap ruling to follow]",
                 ["core/comm/bus.py"], root=str(tmp_path))
    assert v["status"] == "UNGATED", "a deliberate exception must be counted, never a silent pass"
    assert "prod down" in v["detail"]
