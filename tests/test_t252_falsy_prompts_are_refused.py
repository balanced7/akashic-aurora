"""T252 -- falsy non-strings reach paid helpers as their literal repr.

Found by Gemini 3.1 Pro (bus seat `composer`) in a cold review of commits b27aa20..0ff0482.
It reported the JSON-null case. Verification found the class is wider:

    [{"prompt": null}]   -> the model is asked the literal string 'None'
    [null]               -> 'None'
    [{"prompt": 0}]      -> '0'
    [{"prompt": false}]  -> 'False'

ONE EXPRESSION CAUSES ALL FOUR: `str(p.get("prompt", ""))`. `str()` of any falsy non-string
returns a TRUTHY string, so every one of them passes the non-empty check that T245 added for
the express purpose of refusing empty questions -- and a helper is billed to answer 'None'.

WHY T245'S OWN PIN MISSED IT. That pin tested a MISSING key (`{"files": [...]}` with no
prompt). It never tested a key that is PRESENT and falsy. Absent and empty are different
claims -- the same distinction T246 fixed one file over, in the same week, for the same reason.

This is the coercion class recorded earlier today: `str()` at a door turns a wrong value into a
plausible one instead of into an error, so the failure survives every test that only asserts
the call succeeded.
"""
import json

import pytest

from agent_cli import load_fan_prompts


@pytest.mark.parametrize("raw,label", [
    ('[{"prompt": null}]', "object with a null prompt"),
    ('[null]', "bare null element"),
    ('[{"prompt": 0}]', "object with a zero prompt"),
    ('[{"prompt": false}]', "object with a false prompt"),
    ('[{"prompt": "   "}]', "object whose prompt is only whitespace"),
    ('[""]', "bare empty string"),
    ('["   "]', "bare whitespace string"),
])
def test_a_falsy_prompt_is_refused_not_stringified(raw, label):
    """Every one of these was ACCEPTED and sent to a paid helper as its repr."""
    with pytest.raises(ValueError) as e:
        load_fan_prompts(raw)
    assert "0" in str(e.value), (
        f"{label}: the refusal must name the offending INDEX -- in a fan of twenty, "
        f"'something was wrong' is not actionable: {e.value}")


def test_the_refusal_names_the_offending_value():
    """So the caller can see WHICH of their entries is wrong without bisecting the file."""
    with pytest.raises(ValueError) as e:
        load_fan_prompts('[{"prompt": "fine"}, {"prompt": null}]')
    msg = str(e.value)
    assert "1" in msg, f"must name index 1, not index 0: {msg}"
    assert "None" in msg or "null" in msg.lower(), (
        f"must show the value that was refused: {msg}")


def test_a_non_string_prompt_is_refused_even_when_truthy():
    """42 is not a question. str(42) is truthy, which is exactly why this needs saying."""
    with pytest.raises(ValueError):
        load_fan_prompts('[{"prompt": 42}]')


# ------------------------------------------------------------------ no-change paths
def test_arrays_of_real_strings_are_unchanged():
    assert load_fan_prompts(json.dumps(["a", "b", "c"])) == ["a", "b", "c"]


def test_valid_objects_are_unchanged():
    out = load_fan_prompts(json.dumps([{"prompt": "q", "files": ["README.md"]}]))
    assert out[0]["prompt"] == "q" and out[0]["files"] == ["README.md"]


def test_the_fence_separated_form_is_unchanged():
    assert load_fan_prompts("first\n---\nsecond\n") == ["first", "second"]


def test_a_prompt_that_merely_looks_falsy_still_works():
    """'0' as a STRING is a legitimate, if odd, question. Refuse the type, not the content."""
    assert load_fan_prompts('["0"]') == ["0"]
