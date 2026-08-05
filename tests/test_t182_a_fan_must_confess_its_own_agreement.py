"""PRE-REGISTERED ACCEPTANCE (T182) -- N correlated essays may not read as N findings,
and the detector may not read "I cannot tell" as "all clear".

MEASURED. `ask --fan 3` on one question returned three near-identical answers and the aggregate
said "3/3 landed". True, and structurally a lie: a caller reads 3 as three pieces of evidence
when it was one piece billed three times. A five-position wavefront minutes later produced
genuinely different content -- the contrast proving diversity comes from POSITION, not repetition.

THEN THE DETECTOR FAILED ITS OWN CONTROL, which is why this file looks the way it does. The first
cut used one threshold at 0.6. Calibrated against known-outcome controls it scored:

    identical strings                          1.00
    same question x3, paraphrased (REAL case)  0.19   <- read as "diverse". MISS.
    five-position wavefront                    0.011
    disjoint nonsense                          0.00

Word-set Jaccard is brutal on paraphrase, and the module docstring SAID SO before the feature was
built on top of it. So the instrument now has three outputs. Between the bands it does not know,
and answering "distinct" there is the same defect the measurement exists to catch.

THE PIN LESSON, kept deliberately: the first version of this file tested a synthetic near-verbatim
pair, passed, and gave false confidence while the real case failed. K3 now pins the ACTUAL
observed answers from that run. A pin that only exercises the easy case is a pin that lies.

  K1  near-verbatim answers  -> "collapsed", and the fan still reports ok
  K2  genuinely different    -> "distinct"
  K3  the REAL control (one idea, three phrasings) -> "unknown", NEVER "distinct"
  K4  the raw number is always reported, so a later reader may reject the bands and keep the data
  K5  agreement is computed over LANDED branches only -- an outage is not a dissenting voice
  K6  a one-branch fan reports None, not 1.0 -- self-corroboration is fabricated

Run: py -m pytest tests/test_t182_a_fan_must_confess_its_own_agreement.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import ask as A  # noqa: E402


class _Resp:
    def __init__(self, text, finish="stop", pt=100, ct=50):
        self.choices = [type("C", (), {
            "message": type("M", (), {"content": text})(),
            "finish_reason": finish})()]
        self.usage = type("U", (), {"prompt_tokens": pt, "completion_tokens": ct})()


class _Scripted:
    """Answers each prompt from a lookup; a prompt mapped to None raises."""

    def __init__(self, table):
        outer = self

        class _Completions:
            def create(self, model=None, messages=None, max_tokens=None):
                text = outer.table[messages[-1]["content"]]
                if text is None:
                    raise RuntimeError("branch refused")
                return _Resp(text)

        self.table = table
        self.chat = type("Chat", (), {"completions": _Completions()})()


# The REAL control: the three answers T181's first --fan 3 actually returned, verbatim.
# A human reading them calls them one answer. The detector must not call them "distinct".
REAL_A = ("The most common pitfall is decomposing a complex problem into independent sub-tasks, "
          "solving each in a parallel LLM call, and naively combining the outputs, which "
          "silently degrades results because the model loses cross-dependencies, global "
          "coherence, and the ability to resolve contradictions that would be caught in a "
          "single holistic call.")
REAL_B = ("The most common silent failure is decomposing a complex reasoning task into "
          "independent subtasks solved in parallel, which loses cross-dependencies and yields a "
          "globally inconsistent or less coherent answer than a single holistic call.")
REAL_C = ("Parallel fan-out silently degrades results by sacrificing coherence, as independent "
          "calls lack a shared thread and produce subtly contradictory or fragmented "
          "information that a single, sequentially reasoned call would unify.")

VERBATIM = "independent parallel branches lose cross dependencies and global coherence entirely"
DIFFERENT = ("rate limits and tail latency dominate because one slow branch stalls the barrier "
             "while token spend multiplies without extra evidence arriving")


def test_k1_near_verbatim_is_collapsed_and_still_ok():
    o = A.ask_many(["p1", "p2"], client=_Scripted({"p1": VERBATIM, "p2": VERBATIM}))
    assert o.ok and not o.partial, "nothing failed -- agreement is information, not an error"
    assert o.detail["diversity"] == "collapsed"
    assert o.detail["collapsed"] is True


def test_k2_genuinely_different_is_distinct():
    o = A.ask_many(["p1", "p2"], client=_Scripted({"p1": VERBATIM, "p2": DIFFERENT}))
    assert o.detail["diversity"] == "distinct"
    assert o.detail["collapsed"] is False


def test_k3_the_real_control_is_UNKNOWN_never_distinct():
    """THE PIN THAT MATTERS. These three are the answers the live fan actually produced. A
    reader calls them one answer. Lexical overlap scores them 0.19 -- far from verbatim, far
    from unrelated. The honest output is that this instrument cannot tell."""
    o = A.ask_many(["p1", "p2", "p3"],
                   client=_Scripted({"p1": REAL_A, "p2": REAL_B, "p3": REAL_C}))
    assert o.detail["diversity"] == "unknown", (
        f"scored {o.detail['lexical_agreement']} and claimed "
        f"{o.detail['diversity']!r}; one idea in three phrasings is exactly what this metric "
        f"cannot resolve, and 'distinct' there is a false all-clear")
    assert o.detail["collapsed"] is False, "unknown is not a collapse claim either"


def test_k4_the_number_survives_the_bands():
    o = A.ask_many(["p1", "p2", "p3"],
                   client=_Scripted({"p1": REAL_A, "p2": REAL_B, "p3": REAL_C}))
    score = o.detail["lexical_agreement"]
    assert isinstance(score, float) and 0.0 <= score <= 1.0, (
        "bands are a judgement; the number is the evidence. Keep both so a later reader can "
        "reject the thresholds without losing the measurement")


def test_k5_a_failed_branch_is_not_a_dissenting_voice():
    o = A.ask_many(["p1", "p2", "p3"],
                   client=_Scripted({"p1": VERBATIM, "p2": VERBATIM, "p3": None}))
    assert o.partial and o.detail["n_ok"] == 2
    assert o.detail["n_compared"] == 2, "the outage must not be counted as a third opinion"
    assert o.detail["diversity"] == "collapsed"


def test_k6_one_branch_cannot_corroborate_itself():
    o = A.ask_many(["p1"], client=_Scripted({"p1": VERBATIM}))
    assert o.ok
    assert o.detail["lexical_agreement"] is None and o.detail["diversity"] is None
