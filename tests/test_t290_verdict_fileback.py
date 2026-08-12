"""T290 RED -- verdict file-back: fan answers stop being amnesiac, without self-grading.

THE ARC (fence r2, reconciled 2026-08-12 -- docs/library/design/20260812_fence-r2-reconciliation_825c9a.md):
residents answer fans (T261) but nothing remembers whether their answers survived. RC1 lands
the two append-only planes calibration needs:

    residents:verdicts:log        what a branch SAID (filed by the door, one per ask_id)
    residents:adjudications:log   what a NON-AUTHOR later ESTABLISHED (joined on ask_id)

THE LAWS, each bought in the fence:

  H-C1 (Heimdall, high): the `by` field is caller-declared and nothing verifies it, so
       adjudication is OPERATOR-ONLY by default -- `by` must be in adjudicators() AND must
       not equal the verdict's own agent. A resident grading itself is the T255 class.
  H-BLIND: a LESSON citing an ask_id is not an adjudication. Only the adjudication log
       moves calibration -- the learning store is not a back door.
  T178: absence never reads as success. An unadjudicated verdict counts adjudicated=0;
       calibration returns COUNTS (RC2 renders rates with its own n-floors).
  N-FAIRNESS: cold twins are first-class -- `cold_twin_of` records the pairing the
       pre-registered persistence claim needs (>=20 adjudicated pairs per shape).

Pins:
  P1  file_verdict appends one record; unknown question_shape refuses naming the vocabulary;
      empty shape stores as 'undeclared' (visible, never silently dropped)
  P2  duplicate ask_id refuses -- one verdict per ask, dedup is idempotency (LearningStore law)
  P3  adjudicate: non-operator refused naming the rule; operator==verdict-agent refused
      (sock-puppet); adjudication with no filed verdict refused (a record about nothing)
  P4  operator adjudication lands and joins by ask_id; outcome vocabulary enforced
  P5  calibration counts: unadjudicated -> adjudicated=0 confirmed=0; moves after adjudication;
      per-shape pooling present alongside per-(shape,resident) cells
  P6  the lesson back door stays shut: a learn record citing the ask_id changes NOTHING
  P7  cold_twin_of recorded verbatim and filterable (the matched-pair substrate)
  P8  CLI: `resident adjudicate` refuses a non-operator BEFORE any write; `resident
      calibration` renders counts and exits 0 on an empty store ("no data", never a crash)

Run: py -m pytest tests/test_t290_verdict_fileback.py -q
"""
import os
import sys
import subprocess

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed (child inherits via env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402

from core.fleet import verdicts as V  # noqa: E402


def run(*args, timeout=120):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


@pytest.fixture(autouse=True)
def _operators(monkeypatch):
    """A known adjudicator set per test -- the default is env-driven config, not a constant."""
    monkeypatch.setenv("AKASHIC_ADJUDICATORS", "daniil,conductor_x")


# ---------------------------------------------------------------- P1: filing
def test_p1_file_verdict_appends_and_teaches_vocabulary():
    rec = V.file_verdict(agent="deepseek", ask_id="a1", question_shape="descriptive",
                         gist="cursor families disagree at bus.py:412")
    assert rec["agent_id"] == "deepseek" and rec["ask_id"] == "a1"
    assert rec["question_shape"] == "descriptive"
    rows = V.verdicts(agent="deepseek")
    assert len(rows) == 1 and rows[0]["ask_id"] == "a1"

    with pytest.raises(ValueError) as e:
        V.file_verdict(agent="deepseek", ask_id="a2", question_shape="vibes", gist="x")
    for shape in V.SHAPES:
        assert shape in str(e.value), (
            "P1: an unknown shape must refuse WITH the vocabulary -- 422-with-vocabulary, "
            "the grammar law the ask door already obeys")

    rec2 = V.file_verdict(agent="deepseek", ask_id="a3", question_shape="", gist="y")
    assert rec2["question_shape"] == "undeclared", (
        "P1: absence is stored VISIBLY -- an undeclared shape is its own bucket, never a "
        "silent drop and never a guess (T228 declared-not-derived)")


# ---------------------------------------------------------------- P2: idempotency
def test_p2_duplicate_ask_id_refuses():
    V.file_verdict(agent="kimi", ask_id="dup1", question_shape="descriptive", gist="first")
    with pytest.raises(ValueError) as e:
        V.file_verdict(agent="kimi", ask_id="dup1", question_shape="descriptive", gist="again")
    assert "dup1" in str(e.value), "P2: the refusal names the colliding ask_id"


# ---------------------------------------------------------------- P3: refusals
def test_p3_adjudication_refusals():
    V.file_verdict(agent="deepseek", ask_id="j1", question_shape="normative", gist="claim")

    with pytest.raises(ValueError) as e:
        V.adjudicate(ask_id="j1", outcome="confirmed", by="deepseek")
    assert "adjudicat" in str(e.value).lower() and "deepseek" in str(e.value), (
        "P3: a resident outside the operator set is refused BY NAME -- H-C1, operator-only "
        "is the default, not the fallback")

    with pytest.raises(ValueError):
        V.adjudicate(ask_id="j1", outcome="confirmed", by="nobody_at_all")

    # Sock-puppet direct case: even an operator may not adjudicate its OWN verdict.
    V.file_verdict(agent="conductor_x", ask_id="j2", question_shape="descriptive", gist="own")
    with pytest.raises(ValueError) as e2:
        V.adjudicate(ask_id="j2", outcome="confirmed", by="conductor_x")
    assert "own" in str(e2.value).lower() or "self" in str(e2.value).lower(), (
        "P3: author==adjudicator refused even inside the operator set")

    with pytest.raises(ValueError) as e3:
        V.adjudicate(ask_id="never_filed", outcome="confirmed", by="daniil")
    assert "never_filed" in str(e3.value), (
        "P3: an adjudication with no verdict to join is a record about nothing -- refused, "
        "and the refusal names the missing ask_id")


# ---------------------------------------------------------------- P4: the join
def test_p4_operator_adjudication_lands():
    V.file_verdict(agent="deepseek", ask_id="k1", question_shape="descriptive", gist="g")
    rec = V.adjudicate(ask_id="k1", outcome="refuted", by="daniil", receipt="hand-checked")
    assert rec["ask_id"] == "k1" and rec["outcome"] == "refuted" and rec["by"] == "daniil"

    with pytest.raises(ValueError) as e:
        V.adjudicate(ask_id="k1", outcome="maybe", by="daniil")
    assert "confirmed" in str(e.value) and "refuted" in str(e.value), (
        "P4: outcome vocabulary refused WITH the vocabulary")


# ---------------------------------------------------------------- P5: counts, never rates
def test_p5_calibration_counts_absence_honestly():
    V.file_verdict(agent="deepseek", ask_id="c1", question_shape="descriptive", gist="a")
    V.file_verdict(agent="deepseek", ask_id="c2", question_shape="descriptive", gist="b")
    V.file_verdict(agent="kimi", ask_id="c3", question_shape="normative", gist="c")

    cal = V.calibration()
    cell = cal["cells"][("descriptive", "deepseek")]
    assert cell["filed"] == 2 and cell["adjudicated"] == 0 and cell["confirmed"] == 0, (
        "P5: unadjudicated is VISIBLY unadjudicated -- never coerced toward success (T178)")

    V.adjudicate(ask_id="c1", outcome="confirmed", by="daniil")
    cal2 = V.calibration()
    cell2 = cal2["cells"][("descriptive", "deepseek")]
    assert cell2["adjudicated"] == 1 and cell2["confirmed"] == 1 and cell2["filed"] == 2

    pooled = cal2["shapes"]["descriptive"]
    assert pooled["filed"] >= 2 and pooled["adjudicated"] >= 1, (
        "P5: per-shape pooling exists alongside cells -- the fence's convergent counter "
        "(H-C2 + N-C2): shape-level is the primary axis at our n")
    assert not any(k.endswith("rate") for cell in cal2["cells"].values() for k in cell), (
        "P5: RC1 returns COUNTS only; rates belong to RC2's render with its n-floors")


# ---------------------------------------------------------------- P6: the back door
def test_p6_lessons_never_adjudicate():
    V.file_verdict(agent="deepseek", ask_id="bd1", question_shape="descriptive", gist="claim")
    rc, out, err = run("learn", "deepseek", "--experiment", "t290_backdoor_probe",
                       "--tried", "confirming my own answer for ask bd1",
                       "--result", "bd1 confirmed correct, adjudicated")
    assert rc == 0, f"seeding the probe lesson failed: {err or out}"
    cal = V.calibration()
    cell = cal["cells"][("descriptive", "deepseek")]
    assert cell["adjudicated"] == 0, (
        "P6: a lesson CITING an ask_id moves nothing -- adjudication is ONLY the "
        "adjudication record type (Heimdall's BLIND, accepted whole)")


# ---------------------------------------------------------------- P7: matched pairs
def test_p7_cold_twin_recorded_and_filterable():
    V.file_verdict(agent="deepseek", ask_id="w1", question_shape="generative", gist="warm")
    V.file_verdict(agent="blind", ask_id="w1-cold", question_shape="generative", gist="cold",
                   cold_twin_of="w1")
    twins = V.verdicts(cold_twin_of="w1")
    assert len(twins) == 1 and twins[0]["ask_id"] == "w1-cold", (
        "P7: the pairing the pre-registered claim needs (>=20 adjudicated pairs/shape) is "
        "enumerable from the log, not reconstructed from timestamps")


# ---------------------------------------------------------------- P8: the door
def test_p8_cli_refuses_and_renders():
    rc, out, err = run("resident", "adjudicate", "cli1", "--outcome", "confirmed",
                       "--by", "some_rando")
    assert rc == 2, f"P8: non-operator adjudication must refuse pre-write, got rc={rc}"
    assert "adjudicat" in (err or out).lower(), "P8: the refusal teaches the rule"

    rc2, out2, err2 = run("resident", "calibration")
    assert rc2 == 0, f"P8: empty calibration renders, never crashes: {err2 or out2}"
    assert "no " in (out2 or "").lower() or "0" in (out2 or ""), (
        "P8: an empty store says so -- absence rendered, not a blank page")
