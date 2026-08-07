"""T227 RED: one diversity verdict, two fan shapes, and the NEXT MOVE is wrong in one of them.

FOUND BY USING IT, 2026-08-07, then confirmed by a fan against its own source and sharpened by
an adversary arm that argued the fix down to its defensible core.

THE FAN HAS TWO SHAPES SHARING ONE RENDERER:
  --fan N        prompts = [same_prompt] * N -- one model, one system prompt, one user prompt,
                 N concurrent calls. No temperature, no seed, no top_p is set anywhere.
  --prompts-file N DIFFERENT prompts over one shared evidence pack.

Today's five-lens run (five different questions) rendered:

    == DIVERSITY UNKNOWN: lexical 0.06 across 5 branches ... read them, or adjudicate with
       one more call.

You cannot adjudicate between answers to DIFFERENT QUESTIONS. There is no disagreement to
settle -- the branches were never asked the same thing. The instruction is not merely unhelpful
there, it is unrunnable, and it is the kind of confident next-move this repo keeps learning not
to emit.

AND THE READING INVERTS BETWEEN THE SHAPES:
  homogeneous  low agreement  = the model is UNSTABLE on this question
  heterogeneous low agreement = EXPECTED, different questions produce different answers by
                                construction; it says nothing whatever about quality
  heterogeneous HIGH agreement = the real alarm: N different questions produced one answer, so
                                the helpers are emitting boilerplate or ignoring the differences

Today the heterogeneous case rendered "branches genuinely differ" as though it were a result.

WHAT THIS SLICE DELIBERATELY DOES NOT DO, because an adversary lens argued it down and won:
  * NO per-mode thresholds. The T182 controls (identical 1.00, paraphrase 0.19, five-position
    wavefront 0.011, disjoint 0.00) were calibrated MODE-BLIND. Retuning bands per mode would be
    a confident guess with no controls behind it -- the exact move this module exists to refuse,
    and the exact move I declined this morning when a band read inconveniently.
  * NO taxonomy the caller must learn and declare. `homogeneous` is DERIVED from the prompts
    (len(set(prompts)) == 1), never passed. A caller adds nothing and cannot get it wrong.

So: the NUMBER and the BANDS are untouched. Only the prescription changes, and only where it
was wrong. The law is T225's, one door over -- an outcome must leave the caller with a next move
that works.

THE READER IS NOT ALWAYS THE CALLER. The adversary's best objection was that the caller already
knows which shape they launched. True at the call site, false at `ask --get <handle>` for a
BACKGROUNDED fan (T226, shipped hours ago), where whoever reads the record may never have seen
the command. That surface is pinned here too.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


class _Msg:
    def __init__(self, c): self.content = c


class _Choice:
    def __init__(self, c): self.message, self.finish_reason = _Msg(c), "stop"


class _Usage:
    prompt_tokens, completion_tokens, completion_tokens_details = 5, 5, None


class _Resp:
    def __init__(self, c): self.choices, self.usage, self.model = [_Choice(c)], _Usage(), "fake"


def _client(answers):
    seq = list(answers)

    class _Completions:
        def create(self, **kw):
            return _Resp(seq.pop(0) if seq else "x")

    class _Chat:
        def __init__(self): self.completions = _Completions()

    class _C:
        def __init__(self): self.chat = _Chat()
    return _C()


# ------------------------------------------------------------------ the derived flag
def test_a_homogeneous_fan_is_detected_without_being_declared():
    """Derived, never passed. A caller cannot get this wrong because a caller cannot set it."""
    from core.comm.ask import ask_many

    o = ask_many(["same q"] * 3, client=_client(["a", "b", "c"]))
    assert o.detail["homogeneous"] is True


def test_a_heterogeneous_fan_is_detected_without_being_declared():
    from core.comm.ask import ask_many

    o = ask_many(["q1", "q2", "q3"], client=_client(["a", "b", "c"]))
    assert o.detail["homogeneous"] is False


def test_ask_many_grew_no_new_caller_facing_parameter():
    """The adversary's objection, pinned: no taxonomy for anyone to buy into."""
    import inspect
    from core.comm.ask import ask_many

    params = inspect.signature(ask_many).parameters
    for banned in ("homogeneous", "mode", "diversity_mode", "same_prompt"):
        assert banned not in params, f"{banned} must be DERIVED, never declared"


# ------------------------------------------------------------------ the bands do not move
def test_the_calibrated_bands_are_untouched():
    """T182's controls were measured mode-blind. Nothing here re-tunes them."""
    from core.comm import ask as A

    assert A.COLLAPSE_AT == 0.85 and A.DISTINCT_AT == 0.05


def test_the_number_is_identical_in_both_shapes():
    """Same answers, same lexical agreement, whatever the prompts were."""
    from core.comm.ask import ask_many

    answers = ["alpha beta gamma", "delta epsilon zeta", "eta theta iota"]
    hom = ask_many(["q"] * 3, client=_client(list(answers)))
    het = ask_many(["q1", "q2", "q3"], client=_client(list(answers)))

    assert hom.detail["lexical_agreement"] == het.detail["lexical_agreement"]
    assert hom.detail["diversity"] == het.detail["diversity"]


# ------------------------------------------------------------------ the prescription
def test_prescription_exists_for_every_shape_and_verdict():
    from core.comm.ask import diversity_prescription

    for hom in (True, False):
        for verdict in ("collapsed", "distinct", "unknown"):
            line = diversity_prescription(verdict, hom, n_compared=3, score=0.4)
            assert line and len(line) > 20, f"no next move for {verdict}/homogeneous={hom}"


def test_heterogeneous_low_agreement_is_reported_as_expected_not_as_a_result():
    """THE PIN. Different questions produce different answers BY CONSTRUCTION."""
    from core.comm.ask import diversity_prescription

    line = diversity_prescription("distinct", homogeneous=False, n_compared=5, score=0.06)
    low = line.lower()
    assert "expect" in low, "must say this is the null expectation, not a finding"
    assert "genuinely differ" not in low, \
        "the old text read as a positive result for a fan that could not have produced another"


def test_heterogeneous_high_agreement_is_the_alarm():
    """The inversion that carries the real information, and today said nothing."""
    from core.comm.ask import diversity_prescription

    line = diversity_prescription("collapsed", homogeneous=False, n_compared=5, score=0.9)
    low = line.lower()
    assert "boilerplate" in low or "ignor" in low, \
        "N different questions with one answer means the differences were not engaged"


def test_homogeneous_collapse_does_not_claim_verification():
    """Same model, same prompt: agreement is self-consistency, never independent confirmation.

    The delegation literature is explicit that majority aggregation fails exactly when the
    sampling process produces correlated rather than independent solutions, and nothing in this
    door sets temperature, seed or top_p.
    """
    from core.comm.ask import diversity_prescription

    line = diversity_prescription("collapsed", homogeneous=True, n_compared=4, score=0.95)
    low = line.lower()
    assert "correlat" in low or "not independent" in low or "same model" in low


def test_nobody_is_told_to_adjudicate_answers_to_different_questions():
    """The unrunnable instruction that started this slice."""
    from core.comm.ask import diversity_prescription

    line = diversity_prescription("unknown", homogeneous=False, n_compared=5, score=0.06)
    assert "adjudicate" not in line.lower(), \
        "there is no disagreement to settle between answers to different questions"


def test_homogeneous_unknown_may_still_offer_adjudication():
    """Where it IS runnable, it stays -- this slice narrows the claim, it does not delete it."""
    from core.comm.ask import diversity_prescription

    line = diversity_prescription("unknown", homogeneous=True, n_compared=4, score=0.4)
    assert "adjudicate" in line.lower() or "read them" in line.lower()


# ------------------------------------------------------------------ both reading surfaces
def test_the_background_record_carries_the_shape():
    """`ask --get` on a backgrounded fan: the reader may never have seen the command."""
    from core.comm.ask_bg import summarize

    rec = {"handle": "h", "status": "done", "result": {
        "n": 5, "n_ok": 5, "diversity": "distinct", "homogeneous": False,
        "branches": [{"i": i, "ok": True, "partial": False, "answer": f"A{i}"} for i in range(5)]}}
    nxt = summarize(rec)["next"].lower()
    assert "expect" in nxt, "the retrieved fan must not read 'branches genuinely differ' either"


def test_the_cli_renderer_does_not_reimplement_the_prescriptions():
    """One source for the next move, or the two surfaces drift -- T225's lesson, same day.

    The first cut of this pin asserted the CLI literally CALLS diversity_prescription(). It
    does not, and should not: ask_many computes the line once and carries it in
    detail["diversity_next"], so the JSON door, the CLI door and the background record all
    quote one string. The pin was asserting an implementation, not the invariant -- the third
    crude locator I have written today, and the second to fail on the code being better than
    the test. The invariant is that the CLI CONSUMES the shared line and hardcodes none of it.
    """
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    assert "diversity_next" in src, "the CLI must quote the shared prescription"
    for stale in ("branches genuinely differ", "one answer billed",
                  "adjudicate with one more call"):
        assert stale not in src, \
            f"the CLI still hardcodes a prescription ({stale!r}) -- two sources, one question"
