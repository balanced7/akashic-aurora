"""T244 -- one evidence pack for the whole fan makes every standpoint nominal.

`ask_many` calls `build_context` ONCE, outside the per-branch call, and prepends the result to
every branch body. Two consequences, both measured 2026-08-08.

ONE UNUSABLE FILE DAMAGES BRANCHES THAT NEVER ASKED FOR IT. A five-lens run had three of four
`--with` files refused; a lens needing none of them was voided anyway, and paid for.

A DECLARED STANDPOINT IS NOT ENFORCED. In a multispectral run, a band declaring
`evidence_need="surface"` -- meant to read the module the way a newcomer would, from docstrings
and signatures only -- was handed the full implementation, and its finding cited implementation
lines its own standpoint forbids. A tier-3 critic caught it and named the cause exactly: "the
rig gave the full source to all bands." So the perspective was nominal. Asking five helpers to
look from five angles, then showing them all the same thing, measures nothing about angle.

NOT A COST INCREASE, WHICH IS THE PART THAT SURPRISED ME. `shared_ctx` is already prepended to
EVERY branch body, so today every branch pays for the entire pack regardless of what it needs.
Letting a branch declare a narrower need makes the fan cheaper, not dearer.

The budget changes character too, for the better: `build_context` spends one per-call pool
first-come, so a huge first file starves later ones ("skipped"). Per-branch packs give each
branch its own pool, and starvation across unrelated branches stops being expressible.
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


class RecordingClient:
    """Answers everything, and keeps every prompt body it was handed.

    The bodies are the evidence for this whole slice: what a branch was SHOWN is the claim
    under test, and no amount of inspecting the return value can establish it.
    """

    def __init__(self):
        self.bodies = []
        outer = self

        class _Completions:
            def create(self, **kwargs):
                outer.bodies.append(kwargs["messages"][-1]["content"])
                return _Resp("ANSWER")

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


@pytest.fixture
def files(tmp_path):
    (tmp_path / "surface.py").write_text('"""A docstring only."""\n', encoding="utf-8")
    (tmp_path / "deep.py").write_text("SECRET_IMPLEMENTATION_TOKEN = 1\n" * 5, encoding="utf-8")
    return tmp_path


def test_a_branch_can_declare_its_own_evidence(files):
    """The core capability: a dict prompt carries its own files."""
    c = RecordingClient()
    out = ask_mod.ask_many(
        [{"prompt": "surface question", "files": [str(files / "surface.py")]},
         {"prompt": "deep question", "files": [str(files / "deep.py")]}],
        context_root=str(files), client=c)

    assert out.ok, f"fan did not land: {out.why}"
    assert len(c.bodies) == 2, "expected one body per branch"

    surface_body = next(b for b in c.bodies if "surface question" in b)
    deep_body = next(b for b in c.bodies if "deep question" in b)

    assert "SECRET_IMPLEMENTATION_TOKEN" not in surface_body, (
        "the surface branch was shown the implementation it did not ask for. This is the "
        "whole defect: a declared standpoint that is not enforced is nominal, and a fan of "
        "five such standpoints measures nothing about standpoint.")
    assert "SECRET_IMPLEMENTATION_TOKEN" in deep_body, (
        "the deep branch did not receive the file it explicitly requested")


def test_an_unusable_file_damages_only_the_branch_that_asked_for_it(files, tmp_path_factory):
    """Measured: 3 of 4 files refused, and a lens needing none of them was voided anyway."""
    outside = tmp_path_factory.mktemp("outside") / "elsewhere.py"
    outside.write_text("X = 1\n", encoding="utf-8")

    c = RecordingClient()
    out = ask_mod.ask_many(
        [{"prompt": "clean branch", "files": [str(files / "surface.py")]},
         {"prompt": "doomed branch", "files": [str(outside)]}],
        context_root=str(files), client=c)

    branches = (out.detail or {}).get("branches") or []
    assert len(branches) == 2
    clean = next(b for b in branches if "clean branch" in (b.get("prompt") or ""))
    doomed = next(b for b in branches if "doomed branch" in (b.get("prompt") or ""))

    assert not (clean.get("warnings") or []), (
        f"a branch whose own evidence was fine carries a warning about another branch's "
        f"file: {clean.get('warnings')!r}")
    assert doomed.get("warnings"), (
        "the branch whose file was refused (outside the repo root) was not told")


def test_each_branch_record_carries_its_own_evidence_meta(files):
    """Without per-branch meta, a cited claim cannot be traced to what that branch read."""
    c = RecordingClient()
    out = ask_mod.ask_many(
        [{"prompt": "q1", "files": [str(files / "surface.py")]},
         {"prompt": "q2", "files": [str(files / "deep.py")]}],
        context_root=str(files), client=c)

    for b in (out.detail or {}).get("branches") or []:
        ctx = b.get("context")
        assert ctx, f"branch {b.get('i')} carries no evidence meta of its own"
        paths = [i.get("path", "") for i in ctx.get("included", [])]
        assert len(paths) == 1, f"branch {b.get('i')} should have exactly its own file: {paths}"


def test_string_prompts_still_share_with_files(files):
    """Every existing caller must be untouched. --prompts-file sends plain strings."""
    c = RecordingClient()
    out = ask_mod.ask_many(["a", "b"], with_files=[str(files / "deep.py")],
                           context_root=str(files), client=c)

    assert out.ok, f"fan did not land: {out.why}"
    assert len(c.bodies) == 2
    for body in c.bodies:
        assert "SECRET_IMPLEMENTATION_TOKEN" in body, (
            "a string prompt must still receive the shared with_files pack")
    assert (out.detail or {}).get("context"), "the shared pack's meta must still be reported"


def test_identical_file_sets_are_built_once(files, monkeypatch):
    """Memoisation, so N branches sharing a set do not re-read the same file N times.

    Cheap on disk, but the pin exists because the obvious implementation calls build_context
    inside _one() and quietly turns a 20-branch fan into 20 reads of the same file.
    """
    calls = []
    real = ask_mod.build_context

    def counting(paths, **kw):
        calls.append(tuple(paths))
        return real(paths, **kw)

    monkeypatch.setattr(ask_mod, "build_context", counting)

    c = RecordingClient()
    same = [str(files / "deep.py")]
    ask_mod.ask_many([{"prompt": f"q{i}", "files": same} for i in range(4)],
                     context_root=str(files), client=c)

    assert len(calls) == 1, (
        f"four branches shared one file set and build_context ran {len(calls)}x: {calls}")
