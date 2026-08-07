"""
T203 -- `ask --with <paths>`: stop asking blind helpers to reason about code. RED first.

WHY, measured on this session's own fences (2026-08-06). Four times I asked deepseek to
attack a design, describing the code in PROSE because it has no file access. It was right
twice and wrong twice -- and BOTH wrong answers were wrong for the same reason:

  * it argued the arm-time pending check must be BROADER than wake_worthy or the seat goes
    "permanently unwakeable". The polarity is inverted, provable in four lines at
    bifrost_api.py:252 (`return live` -> the watcher EXITS; falling through -> it BLOCKS).
    It could not read those four lines.
  * it built a deafness scenario on an ask-id being REUSED after a crash. Ask ids are Redis
    XADD stream ids -- monotonic, never reissued. One look at the send path settles it.

I caught both by reading the source myself, which is exactly the work I was delegating.
The helper's blindness, not its intelligence, capped the quality of every fence.

THE FIX IS SMALL AND STRUCTURAL: put the source in the prompt, WITH LINE NUMBERS, so the
answer can cite file:line and be cheap to verify. A claim carrying a citation is falsifiable
in seconds; a claim from prose costs a manual investigation.

HONESTY REQUIREMENTS, because a context assembler that lies is worse than no assembler:
  * an unreadable path is NAMED, never silently skipped -- a helper reasoning from files it
    did not receive, while believing it did, is the blind case with extra confidence
  * truncation is CONFESSED in the prompt itself (so the model knows it is partial) AND in
    the outcome detail (so the caller does)
  * the budget is per-CALL, not per-file: three files sharing one ceiling, first-come, so a
    huge first file cannot silently starve the rest without saying so

Run: py -m pytest tests/test_t203_ask_with_files.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import ask as ask_mod  # noqa: E402


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "a.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("x" * 500, encoding="utf-8")
    return tmp_path


def test_files_are_inlined_with_path_and_line_numbers(tree):
    """Line numbers are the whole point: they are what make `file:line` citations
    possible, and a citation is what makes an answer cheap to verify."""
    block, meta = ask_mod.build_context([str(tree / "a.py")], root=tree)
    assert "a.py" in block
    assert "1" in block and "alpha" in block
    lines = [ln for ln in block.splitlines() if "alpha" in ln]
    assert lines and lines[0].strip().startswith("1"), "line number must precede the line"
    assert meta["included"] and meta["included"][0]["path"].endswith("a.py")


def test_an_unreadable_path_is_named_not_silently_dropped(tree):
    """The failure this pin exists for: a helper reasoning from files it never received,
    while believing it did. Worse than blind, because it is blind AND confident."""
    block, meta = ask_mod.build_context([str(tree / "a.py"), str(tree / "nope.py")], root=tree)
    assert meta["missing"], "an unreadable path must be reported"
    assert any("nope.py" in m["path"] for m in meta["missing"])
    assert "nope.py" in block, "the PROMPT must say the file could not be read"


def test_truncation_is_confessed_in_both_directions(tree):
    """The model must know its view is partial (or it will reason as if complete), and so
    must the caller (or they will trust a conclusion drawn from a fragment)."""
    block, meta = ask_mod.build_context([str(tree / "b.py")], budget_chars=100, root=tree)
    assert meta["truncated"], "caller side"
    assert any(w in block.lower() for w in ("truncat", "cut", "partial")), "model side"


def test_budget_is_per_call_and_starvation_is_reported(tree):
    """Three files, one ceiling. A file that got NO room must appear in the report --
    silently dropping it recreates the confident-blindness failure one layer down."""
    big = tree / "big.py"
    big.write_text("y" * 5000, encoding="utf-8")
    block, meta = ask_mod.build_context([str(big), str(tree / "a.py")], budget_chars=200, root=tree)
    names = [i["path"] for i in meta["included"]] + [s["path"] for s in meta.get("skipped", [])]
    assert any("a.py" in n for n in names), "a starved file must still be accounted for"
    assert len(block) < 2000


def test_no_path_escapes_the_repo(tmp_path):
    """A prompt assembler is a read primitive pointed at whatever it is handed. Keep it
    inside the repo so a stray path cannot exfiltrate a key file into a model prompt."""
    block, meta = ask_mod.build_context(["../../../../etc/passwd"])
    assert not meta["included"], "outside-repo paths must not be inlined"
    assert meta["missing"] or meta.get("refused")


def test_empty_list_is_a_noop_not_an_error():
    block, meta = ask_mod.build_context([])
    assert block == "" and not meta["included"]


def test_ask_accepts_with_and_records_what_it_sent(monkeypatch, tree):
    """The outcome must say which files the answer was based on -- otherwise a cited
    claim cannot be traced back to the version of the file that was actually read."""
    seen = {}

    class FakeResp:
        class C:
            class M:
                content = "ok"
            message = M()
            finish_reason = "stop"
        choices = [C()]
        usage = None

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    seen["messages"] = kw.get("messages")
                    return FakeResp()

    o = ask_mod.ask("why", with_files=[str(tree / "a.py")], client=FakeClient(),
                     context_root=tree)
    assert o.ok
    assert "alpha" in str(seen["messages"]), "file content must reach the model"
    assert o.detail.get("context", {}).get("included"), "outcome records what it sent"


def test_with_files_reaches_the_FAN_not_only_the_single_ask(tree):
    """FOUND WHILE PLAYING, and it was a SILENT no-op. --with was accepted on --fan and
    --prompts-file and did nothing: with_files was threaded into the single-ask path and
    never into ask_many. Five helpers in a 5-way fan correctly answered 'I cannot answer,
    the files were not attached' -- the flag had simply evaporated between the door and
    the worker.

    Silent flag-drop is the worst shape available: the command succeeds, the answers look
    well-formed, and only a reader who knows what SHOULD have been in the prompt can tell.
    Built once per fan rather than per branch, so N branches share one context read."""
    seen = []

    class FakeResp:
        class C:
            class M:
                content = "ok"
            message = M()
            finish_reason = "stop"
        choices = [C()]
        usage = None

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    seen.append(str(kw.get("messages")))
                    return FakeResp()

    o = ask_mod.ask_many(["q1", "q2"], client=FakeClient(),
                         with_files=[str(tree / "a.py")], context_root=tree)
    assert o.ok
    assert len(seen) == 2
    for msg in seen:
        assert "alpha" in msg, "every branch must receive the inlined file"
    assert o.detail.get("context", {}).get("included")


def test_context_block_is_delimited_so_prose_and_code_cannot_blur():
    """A model that cannot tell the question from the source will answer about the
    wrong one. Cheap to guarantee, expensive to debug."""
    block, _ = ask_mod.build_context([__file__], budget_chars=400)
    assert block.count("---") >= 2 or block.count("===") >= 2 or "```" in block
