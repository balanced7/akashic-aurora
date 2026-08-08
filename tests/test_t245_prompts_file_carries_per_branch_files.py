"""T245 -- T244 shipped built but not wired, and I found it in my own slice.

`ask_many` learned to take `{"prompt": ..., "files": [...]}` so a branch can declare the
evidence its standpoint allows (T244). The CLI door then did:

    prompts = [str(p) for p in loaded]

so every element is stringified. The capability is unreachable from `--prompts-file`, and the
failure is SILENT and plausible: the dict becomes its own Python repr and is sent as the
prompt, so a helper receives `{'prompt': 'audit this', 'files': ['x.py']}` as its question and
answers it. Exactly what the T244 RED pin caught one layer down.

This is the check_wiring class the repo already tracks, in the shape it is hardest to see: the
function IS called, the flag IS accepted, and the DATA that gives it meaning is destroyed in
transit.

The parsing lived inline inside `cmd_ask` and so could not be pinned at all -- which is the
second half of why this shipped. A unit that cannot be tested is a unit that will drift.
"""
import json

import pytest

from agent_cli import load_fan_prompts


def test_a_json_array_of_dicts_survives_parsing(tmp_path):
    """The core wiring. What the caller wrote must reach ask_many with its shape intact."""
    p = tmp_path / "prompts.json"
    p.write_text(json.dumps([
        {"prompt": "surface question", "files": ["README.md"]},
        {"prompt": "deep question", "files": ["core/comm/ask.py"]},
    ]), encoding="utf-8")

    out = load_fan_prompts(p.read_text(encoding="utf-8"))

    assert isinstance(out[0], dict), (
        f"the dict was stringified in transit: {out[0]!r}. A helper would have received the "
        "repr as its question and answered it, which is why this failed silently.")
    assert out[0]["files"] == ["README.md"]
    assert out[1]["prompt"] == "deep question"


def test_a_dict_without_a_prompt_is_refused_by_index(tmp_path):
    """Loudly, and naming which one.

    The quiet alternative is an empty branch: a paid-for helper asked nothing, answering
    nothing, indistinguishable in the results from a helper that found nothing.
    """
    raw = json.dumps([{"prompt": "fine", "files": []}, {"files": ["x.py"]}])
    with pytest.raises(ValueError) as e:
        load_fan_prompts(raw)
    assert "1" in str(e.value), f"the message must name the offending index: {e.value}"


def test_plain_string_arrays_are_unchanged(tmp_path):
    """Every existing caller. This is the majority path and it must not move."""
    assert load_fan_prompts(json.dumps(["a", "b", "c"])) == ["a", "b", "c"]


def test_the_fence_separated_form_is_unchanged():
    """Not JSON -> split on a line containing only ---, so a prompt may be multi-line."""
    raw = "first prompt\nstill first\n---\nsecond prompt\n"
    assert load_fan_prompts(raw) == ["first prompt\nstill first", "second prompt"]


def test_a_bare_json_object_is_not_mistaken_for_a_fan():
    """json.loads succeeds on a lone object; it is not a list of prompts.

    Today the isinstance(list) check sends it to the fence path, where it becomes ONE prompt
    containing raw JSON. Pinned so that stays deliberate rather than incidental.
    """
    out = load_fan_prompts('{"prompt": "just one"}')
    assert len(out) == 1, f"a lone object must not fan out: {out!r}"
