"""T242 -- the evidence notice must guard the BOUNDARY, not just the DOOR.

WHY THIS PIN EXISTS, measured 2026-08-08.

T218 and T225 built a correct notice: when `--with` evidence is clipped, refused, missing or
skipped, the caller who will draw a conclusion from it gets told. T237 gave JSON callers a
discoverable `warnings` list. All three shipped, all three are pinned, and all three fixed
`agent_cli.py`.

`unusable_evidence_notice` is called from THREE sites, every one of them in agent_cli.py, plus
its own tests. The token "warnings" appears ZERO times in core/comm/ask.py.

So the guard lives at the CLI door. Anything that IMPORTS the library -- every script, every
harness, every other module, which is most of what this fleet actually runs -- receives
`detail["context"]` and no notice whatsoever. Not a bug in the notice: a layer mismatch.

It was paid for the same day. A multispectral harness imported `ask_many` directly, was clipped
at 40,000 chars (line 744 of an 889-line file), and every branch went blind on exactly the
region under study. `context.truncated` was `True` in the returned detail the entire time. The
run was repeated and the notice was missed AGAIN, because nothing on the library path renders
it and the reader has to already know the field is there.

This is the T160 class one level up: the function IS called, but only on the path a human takes.

Daniil, 2026-08-08, on why this shape recurs: a fact must be glanceable and must carry the SENSE
it is true in. "The clipped-evidence warning exists" is TRUE at the CLI door and FALSE at the
library boundary. Stated unqualified, it does not merely omit -- it lies, and it told a caller
it was protected while it was not.
"""
import pytest

from core.comm import ask as ask_mod


# --------------------------------------------------------------------------- fakes
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
    """Enough of the OpenAI-compatible surface for ask()/ask_many(), and no network.

    Deliberately NOT a mock of build_context: the whole point is to exercise the real
    evidence path and assert on what the real boundary hands back.
    """
    chat = _Chat()


@pytest.fixture
def clipped_file(tmp_path, monkeypatch):
    """A file guaranteed to exceed the context budget, inside an allowed root."""
    monkeypatch.setattr(ask_mod, "DEFAULT_CONTEXT_CHARS", 200, raising=False)
    p = tmp_path / "big.py"
    p.write_text("\n".join(f"# line {i} " + "y" * 40 for i in range(200)), encoding="utf-8")
    return p


@pytest.fixture
def clean_file(tmp_path):
    p = tmp_path / "small.py"
    p.write_text("VALUE = 1\n", encoding="utf-8")
    return p


# --------------------------------------------------------------------------- the pins
def test_ask_tells_a_library_caller_its_evidence_was_clipped(clipped_file, tmp_path):
    """The core defect. A caller who never touches agent_cli must still be warned."""
    out = ask_mod.ask("q", with_files=[str(clipped_file)], context_root=str(tmp_path),
                      client=FakeClient())
    d = out.detail or {}

    assert d.get("context", {}).get("truncated") is True, (
        "fixture is wrong -- this test is meaningless unless the evidence really was clipped")

    warn = d.get("warnings")
    assert warn, (
        "a LIBRARY caller got clipped evidence and no warning. detail carried "
        f"context={d.get('context')!r} but no 'warnings' key. This is the whole defect: the "
        "notice is rendered in agent_cli.py and nothing on the import path renders it.")
    assert any("CLIP" in str(w).upper() for w in (warn if isinstance(warn, list) else [warn])), (
        f"warnings present but does not name the clip: {warn!r}")


def test_ask_many_tells_a_library_caller_too(clipped_file, tmp_path):
    """The fan path is where this was actually paid for -- N branches, one shared pack."""
    out = ask_mod.ask_many(["a", "b"], with_files=[str(clipped_file)],
                           context_root=str(tmp_path), client=FakeClient())
    d = out.detail or {}

    assert d.get("context", {}).get("truncated") is True, "fixture is wrong -- nothing was clipped"

    warn = d.get("warnings")
    assert warn, (
        "ask_many handed back N branches built on CLIPPED shared evidence with no warning. "
        "Measured 2026-08-08: 5 branches, 40000 chars, line 744 of 889, twice.")


def test_clean_evidence_carries_no_warnings_key_at_all(clean_file, tmp_path):
    """T237's own rule, and it is load-bearing.

    'Absent when clean: a warnings key that always appears gets filtered out mentally.' A
    warning that is always present is not a warning, it is a banner -- which is precisely how
    a real one goes unread.
    """
    out = ask_mod.ask("q", with_files=[str(clean_file)], context_root=str(tmp_path),
                      client=FakeClient())
    d = out.detail or {}
    assert d.get("context", {}).get("truncated") is False, "fixture is wrong -- evidence was clipped"
    assert "warnings" not in d, (
        f"clean evidence must carry NO warnings key, got {d.get('warnings')!r}")


def test_the_notice_has_exactly_one_implementation(clean_file):
    """Structural guard against the fix that would re-open this.

    The obvious way to satisfy the pins above is to render the string a second time inside
    ask(). Then two places compute the same notice and they drift -- which is the exact risk
    unusable_evidence_notice's own docstring names as the reason it lives beside
    build_context. agent_cli must CONSUME the boundary's warnings, not recompute them.
    """
    import ast
    import pathlib

    cli = pathlib.Path(__file__).resolve().parents[1] / "agent_cli.py"
    tree = ast.parse(cli.read_text(encoding="utf-8", errors="replace"))
    calls = sum(
        1 for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and (getattr(n.func, "attr", None) == "unusable_evidence_notice"
             or getattr(n.func, "id", None) == "unusable_evidence_notice"))
    assert calls == 0, (
        f"agent_cli.py still calls unusable_evidence_notice {calls}x. After T242 the boundary "
        "mints the notice and the door RENDERS what it is handed; a door that recomputes it "
        "is a second implementation that will drift from the first.")
