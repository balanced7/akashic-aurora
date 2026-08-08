"""T247 -- I introduced a sense-collision on the same day I spent removing them.

T244 attached the evidence notice to a branch record only when that branch brought its own
files. A branch riding the fan-wide pack got nothing -- even when the fan-wide pack was clipped.

Verified: a two-branch fan over a 53k file at the 40k budget returns top-level warnings, and
BOTH branch records carry no `warnings` key.

WHY THIS IS WORSE THAN THE STATE BEFORE T244. Before, no branch ever carried the key, so no
caller read it per-branch -- absence carried no information and misled nobody. Now some
branches carry it and some do not, so absence became ambiguous:

    "branch 3 has no warnings"
        TRUE  in the sense: the files THIS branch named were fine
        FALSE in the sense: the evidence THIS branch was given was fine

That is precisely the shape T242 existed to remove -- a fact stated without the sense it is
true in does not merely omit, it misleads -- and I reintroduced it one layer down while
fixing it one layer up. A caller iterating branches reads silence as safety, which is the
failure mode that cost two runs on 2026-08-08.

Found by the adversarial branch of the first fence review run after four self-verified slices.
It arrived with its own disconfirming check attached, which is what settled it in one command
rather than an argument.

THE JUSTIFICATION I USED FOR THE OMISSION WAS ABOUT THE WRONG FIELD. I skipped shared-pack
branches to avoid repeating the same meta N times in the payload. That reasoning applies to
`context` -- a whole nested dict -- and not to `warnings`, which is a short string. I applied a
real constraint to the field it did not govern.
"""
import pytest

from core.comm import ask as ask_mod


class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)
        self.finish_reason = "stop"


class _Usage:
    prompt_tokens = 10
    completion_tokens = 5


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]
        self.usage = _Usage()


class _Completions:
    def create(self, **kwargs):
        return _Resp("ANSWER")


class _Chat:
    completions = _Completions()


class FakeClient:
    """Module-level nesting, deliberately.

    The first draft declared these INSIDE FakeClient, where a sibling class is not in scope at
    class-definition time -- so the file died at collection with a NameError and the pin was
    red for a reason that had nothing to do with the defect. Which is the trap named two
    commits earlier: a RED pin must fail for its stated reason or it proves nothing.
    """

    chat = _Chat()


@pytest.fixture
def big_and_small(tmp_path, monkeypatch):
    monkeypatch.setattr(ask_mod, "DEFAULT_CONTEXT_CHARS", 300, raising=False)
    big = tmp_path / "big.py"
    big.write_text("\n".join(f"# line {i} " + "y" * 40 for i in range(120)), encoding="utf-8")
    small = tmp_path / "small.py"
    small.write_text("OK = 1\n", encoding="utf-8")
    return tmp_path, big, small


def test_a_shared_pack_branch_is_told_its_evidence_was_clipped(big_and_small):
    """The defect. Silence must not mean 'fine' for one branch and 'unknown' for another."""
    root, big, _small = big_and_small
    out = ask_mod.ask_many(["q1", "q2"], with_files=[str(big)],
                           context_root=str(root), client=FakeClient())
    branches = (out.detail or {})["branches"]

    assert (out.detail or {}).get("warnings"), "fixture is wrong -- nothing was clipped"
    for b in branches:
        assert b.get("warnings"), (
            f"branch {b['i']} rode a CLIPPED fan-wide pack and carries no warning. A caller "
            "iterating branches reads that silence as safety -- which is the exact failure "
            "that cost two runs on 2026-08-08.")


def test_a_clean_branch_in_a_damaged_fan_stays_clean(big_and_small):
    """The other half, and the reason this is not just 'warn everywhere'.

    If every branch inherits every warning, the per-branch signal is noise and the caller is
    back to distrusting the whole run -- which T244 shipped to end.
    """
    root, big, small = big_and_small
    out = ask_mod.ask_many([{"prompt": "clean", "files": [str(small)]},
                            {"prompt": "damaged", "files": [str(big)]}],
                           context_root=str(root), client=FakeClient())
    by_prompt = {b["prompt"][:5]: b for b in (out.detail or {})["branches"]}

    assert not (by_prompt["clean"].get("warnings") or []), (
        f"a branch with its own clean evidence inherited another's damage: "
        f"{by_prompt['clean'].get('warnings')!r}")
    assert by_prompt["damag"].get("warnings"), "the damaged branch must still be named"


def test_every_branch_names_where_its_evidence_came_from(big_and_small):
    """So absence of warnings means exactly one thing, and the reader can tell which.

    'no warnings' is only interpretable next to 'and here is what I was given'.
    """
    root, big, small = big_and_small
    out = ask_mod.ask_many([{"prompt": "own", "files": [str(small)]}, "shared"],
                           with_files=[str(small)],
                           context_root=str(root), client=FakeClient())

    for b in (out.detail or {})["branches"]:
        assert b.get("evidence") in ("own", "fan", "none"), (
            f"branch {b['i']} does not say where its evidence came from: {b.get('evidence')!r}")


def test_a_fan_with_no_evidence_at_all_says_so(big_and_small):
    """No files anywhere is a third state, and it must not read as 'clean evidence'."""
    root, _big, _small = big_and_small
    out = ask_mod.ask_many(["q"], context_root=str(root), client=FakeClient())
    b = (out.detail or {})["branches"][0]
    assert b.get("evidence") == "none", f"expected 'none', got {b.get('evidence')!r}"
    assert not (b.get("warnings") or []), "no evidence requested is not a warning"
