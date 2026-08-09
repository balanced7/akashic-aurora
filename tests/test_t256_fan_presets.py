"""T256 -- a preset is a contract AND its parser, held together so they cannot drift.

MEASURED FRICTION, 2026-08-08. Five fan-outs ran today. Every one began with a hand-written
Python builder to assemble a prompts file, and ended with a SECOND throwaway script to regex the
answers apart. The second script is where the errors were, every time:

  - read the INTENT line instead of the WILL-YOU field and reported "8 of 8" when it was 7 of 8
  - a flag counter read a bulleted "**Yes**" as unclear, in 4 of 8 rows
  - a census grader iterated a JSON string character by character and reported an empty result

None of those was a defect in the fan. All three were parsing defects in code written once and
thrown away, which is exactly the code nobody pins.

SO THE POINT OF A PRESET IS NOT TO SAVE TYPING. It is that a KNOWN CONTRACT MAKES THE OUTPUT
MACHINE-READABLE -- and the only way to keep a parser honest is to store it next to the contract
it parses, so a change to one is a change to both.

The slice is deliberately narrow: one preset (`findings`) and lens plumbing. That pair covers
four of the five fans run today.
"""
import pytest

from core.comm import presets


# ---------------------------------------------------------------- the registry contract
def test_a_preset_carries_both_a_contract_and_a_parser():
    """The whole design. A contract with no parser is the situation we already had."""
    p = presets.get("findings")
    assert p.contract and isinstance(p.contract, str)
    assert callable(p.parse)


def test_a_preset_cannot_be_registered_without_a_parser():
    """Enforced at registration, not by convention.

    A contract shipped without its parser is how the two drift -- and drift here means the
    caller silently goes back to hand-rolling a regex, which is the defect this task exists
    to remove.
    """
    with pytest.raises(ValueError):
        presets.register("halfbaked", contract="ANSWER: something", parse=None)


def test_unknown_preset_names_the_known_ones():
    with pytest.raises(KeyError) as e:
        presets.get("nope")
    assert "findings" in str(e.value), "the error must teach what IS available"


# ---------------------------------------------------------------- the contract's content
def test_the_findings_contract_carries_the_clauses_that_earned_their_place():
    """These are not style. Each was measured this week.

    'cheapest thing that would prove you wrong' settled 3 of 7 findings in one command each.
    'abstention is a real answer' produced the NOT-EXPLOITABLE that became a control.
    'descriptive, not normative' is the T207 danger zone -- a grounded helper answering a
    should/better question came back confidently wrong WITH accurate citations.
    """
    c = presets.get("findings").contract.lower()
    assert "wrong" in c, "must demand the cheapest disproof"
    assert "blind" in c, "must demand what the evidence cannot show"
    assert any(w in c for w in ("unclear", "abstention", "abstain")), \
        "must make abstention explicitly acceptable"
    assert "descriptive" in c or "not recommend" in c, "must steer away from normative answers"


# ---------------------------------------------------------------- parsing
FINDINGS_ANSWER = """
FINDINGS:
1. The cursor advances before the write lands, at bus.py:249.
2. The retry path drops the lane, at bus.py:265.

REASONING: traced both cursor families; ruled out the third because it is read-only.

CHECK: kill the process between the two lines and re-read the cursor.

BLIND: cannot see whether any caller depends on the current ordering.
"""


def test_parse_returns_structured_findings():
    out = presets.get("findings").parse(FINDINGS_ANSWER)
    assert out["ok"] is True
    assert len(out["findings"]) == 2
    assert "bus.py:249" in out["findings"][0]
    assert out["check"] and out["blind"]
    assert "read-only" in out["reasoning"]


def test_an_answer_that_ignores_the_contract_is_UNPARSED_not_dropped():
    """A silent drop here would be the failure this whole system keeps paying for.

    An unparseable branch is a REPORTED state, so the caller can read it by hand. Discarding it
    would mean a paid answer vanishing into a clean-looking result -- which is how a fan starts
    lying about its own coverage.
    """
    out = presets.get("findings").parse("I had a nice think about it and everything seems fine.")
    assert out["ok"] is False
    assert out["raw"], "the original text must survive so a human can still read it"
    assert out.get("findings") == []


def test_parse_is_lenient_about_shape_but_strict_about_presence():
    """Models bullet, bold and number inconsistently. That must not lose a finding."""
    messy = ("FINDINGS\n- **first** thing at a.py:1\n* second thing at b.py:2\n\n"
             "REASONING\nbecause\n\nCHECK\nrun it\n\nBLIND\nnothing")
    out = presets.get("findings").parse(messy)
    assert out["ok"] is True and len(out["findings"]) == 2, out


# ---------------------------------------------------------------- lens plumbing
def test_lenses_become_one_branch_each_with_the_contract_appended():
    prompts = presets.build_prompts("findings", ["what does it do", "what breaks it"])
    assert len(prompts) == 2
    for p, lens in zip(prompts, ["what does it do", "what breaks it"]):
        assert p.startswith(lens), "the lens leads; the contract follows"
        assert "BLIND" in p, "every branch carries the contract"


def test_lens_file_ignores_blanks_and_comments(tmp_path):
    f = tmp_path / "lenses.txt"
    f.write_text("# the surface\nwhat does it promise\n\n  \n# the mechanism\nwhat does it do\n",
                 encoding="utf-8")
    assert presets.read_lens_file(str(f)) == ["what does it promise", "what does it do"]


def test_an_empty_lens_file_is_refused_by_name(tmp_path):
    """An empty fan is not an empty result -- it is a caller mistake, and saying so is cheaper
    than returning zero branches that read like 'nothing found'."""
    f = tmp_path / "empty.txt"
    f.write_text("# only comments\n\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        presets.read_lens_file(str(f))
    assert "empty.txt" in str(e.value)


def test_a_single_string_lens_is_one_branch_not_one_per_character():
    """Found by this module's OWN first real fan-out, minutes after it was written.

    `build_prompts("findings", "what does it do")` produced TWELVE branches -- one per character
    -- each a paid API call asking the model "w", then "h", then "a". Fifth instance of this
    class in one session. A string is iterable, so iterating a value that might be one fails
    silently and plausibly rather than loudly.
    """
    out = presets.build_prompts("findings", "what does it do")
    assert len(out) == 1, f"a single string lens must be ONE branch, got {len(out)}"
    assert out[0].startswith("what does it do")
