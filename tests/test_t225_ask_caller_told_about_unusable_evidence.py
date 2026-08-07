"""T225 RED: `--with` tells the caller when evidence was CLIPPED, and nothing when it was REFUSED.

FOUND BY RUNNING THE FAN AT ITS OWN DOOR, 2026-08-07 (pre-registered:
research/in-flight/prereg-ask-ergonomics-fan-2026-08-07.md). Five lenses, one evidence pack of
four files. Three of the four were REFUSED -- they sat outside the repo root, which
build_context is right to refuse, because a prompt assembler that reads anything can lift a
secret into a model prompt.

The refusal was correct. The SILENCE about it was not:

  * stderr: 0 bytes. Not one character about three missing files.
  * $0.065 spent on a fan whose evidence pack was 25% delivered.
  * LENS 1 could not answer at all -- its only file was refused -- and abstained, correctly.
    I paid full price for a branch that was structurally incapable of answering.

T218 closed exactly this asymmetry for the CLIP class and its docstring states the law:
"a clip is only safe if the party who will draw a conclusion from it is told." REFUSED and
MISSING are the same law's other two cases, and T218's `clipped_evidence_notice` returned ""
for both because it gated on `ctx_meta["truncated"]` alone. The data is already there and
correct -- build_context records {"refused": [...], "missing": [...]} -- and nothing read it.
`unusable_evidence_notice` supersedes that name outright: a delegating alias kept for
compatibility would have been a second answer to one question with no caller, and
check_wiring refused it on exactly those grounds.

REFUSED IS STRICTLY WORSE THAN CLIPPED. A clipped file delivers most of itself; a refused file
delivers nothing, so a lens grounded in it is not degraded but VOID. The caller's next move
differs too: a clip means narrow the question, a refusal means move the file into the repo or
pass a different path. One notice cannot stand in for the other.

THE HELPER HALF ALREADY WORKS, AND IT IS WHY THIS COST ONLY MONEY. build_context emits, in
band, `--- COULD NOT READ <path> (outside the repo root) -- do not assume its contents ---`,
and the helper obeyed it exactly: it refused to answer and named the file it lacked. That
in-band line is an anti-confabulation device and it earned its keep here. The defect is that
the same fact never reaches the human who is about to conclude something from the answer.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def test_build_context_records_refusals_and_misses():
    """Precondition: the data the caller needs already exists and is correct."""
    from core.comm.ask import build_context

    outside = str(Path(REPO).anchor) + "definitely_not_in_this_repo_t225.txt"
    _ctx, meta = build_context(["README.md", outside, "no/such/file/t225.py"], root=str(REPO))

    assert [r["path"] for r in meta["refused"]] == [outside], \
        "a path outside the repo root must be REFUSED, and recorded as such"
    assert meta["refused"][0]["why"] == "outside the repo root"
    assert [m["path"] for m in meta["missing"]] == ["no/such/file/t225.py"], \
        "an unreadable path must be recorded as MISSING, distinctly from a refusal"
    assert meta["included"], "the readable file must still be delivered -- one bad path is not a fan-wide failure"


def test_helper_is_warned_in_band_about_a_refused_file():
    """The half that already works, pinned so a refactor cannot quietly drop it.

    This line is why the fan cost only money and not a wrong conclusion: the helper read it
    and abstained instead of confabulating.
    """
    from core.comm.ask import build_context

    outside = str(Path(REPO).anchor) + "definitely_not_in_this_repo_t225.txt"
    ctx, _meta = build_context(["README.md", outside], root=str(REPO))

    assert "COULD NOT READ" in ctx
    assert "do not assume its contents" in ctx


def test_caller_is_told_when_its_evidence_was_refused():
    """THE PIN. Refused evidence must produce a caller-facing notice, as a clip does.

    RED until the notice covers the class rather than one member of it.
    """
    from core.comm.ask import build_context, unusable_evidence_notice

    outside = str(Path(REPO).anchor) + "definitely_not_in_this_repo_t225.txt"
    _ctx, meta = build_context(["README.md", outside], root=str(REPO))

    notice = unusable_evidence_notice(meta)
    assert notice, "three refused files produced 0 bytes of caller-facing output -- that is the defect"
    assert "REFUSED" in notice
    assert "outside the repo root" in notice, "the caller's next move depends on WHY, not just that"
    assert "definitely_not_in_this_repo_t225.txt" in notice, "name the file; a count is not actionable"


def test_caller_is_told_when_its_evidence_was_missing():
    """A typo'd path is the commonest case and today it is silent."""
    from core.comm.ask import build_context, unusable_evidence_notice

    _ctx, meta = build_context(["README.md", "no/such/file/t225.py"], root=str(REPO))

    notice = unusable_evidence_notice(meta)
    assert notice and "MISSING" in notice
    assert "no/such/file/t225.py" in notice


def test_the_three_classes_are_reported_together_and_stay_distinguishable():
    """One call, three failure modes, three different next moves. A merged blob is not a fix."""
    from core.comm.ask import build_context, unusable_evidence_notice

    outside = str(Path(REPO).anchor) + "definitely_not_in_this_repo_t225.txt"
    _ctx, meta = build_context(
        ["core/comm/bus.py", outside, "no/such/file/t225.py"], root=str(REPO))

    notice = unusable_evidence_notice(meta)
    assert "CLIPPED" in notice and "REFUSED" in notice and "MISSING" in notice, \
        "bus.py clips at the 40k budget; the other two are refused and missing"
    assert notice.count("--") >= 1, "each class must carry its own next move, not one shared one"


def test_caller_is_told_when_a_file_was_starved_by_the_budget():
    """The fourth class, and the quietest: file 5 gets zero bytes because 1-4 ate the budget.

    build_context already records it as `skipped`; nothing read that either.
    """
    from core.comm.ask import build_context, unusable_evidence_notice

    _ctx, meta = build_context(["core/comm/bus.py", "README.md"], budget_chars=500, root=str(REPO))
    assert meta["skipped"], "a 500-char budget cannot reach the second file"

    notice = unusable_evidence_notice(meta)
    assert "SKIPPED" in notice and "README.md" in notice


def test_a_clean_evidence_pack_stays_silent():
    """The notice must not become noise: nothing wrong, nothing said."""
    from core.comm.ask import build_context, unusable_evidence_notice

    _ctx, meta = build_context(["README.md"], root=str(REPO))
    assert unusable_evidence_notice(meta) == ""


def test_both_cli_doors_use_the_widened_notice():
    """Single-ask AND fan must both call it. Found the hard way, in this slice.

    The edit that widened the two call sites was applied with replace-all and matched only
    one of them -- the two lines differ by four spaces of indentation, one being inside the
    fan block. The single-ask path stayed on the CLIP-only notice and the live re-run of the
    original scenario printed nothing, which read as "the fix does not work" rather than
    "the fix reached one door". Pinned by COUNT so a future edit cannot half-land either.
    """
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    assert src.count("ask_mod.unusable_evidence_notice(") == 2, \
        "both the fan render and the single-ask render must use the widened notice"
    assert "clipped_evidence_notice" not in src, \
        "no CLI door should still reach for the retired CLIP-only name"


def test_t218_notice_survives_as_the_clip_case():
    """T218's guarantee is unchanged in substance -- only the function's name moved.

    Its pins now import `unusable_evidence_notice` and assert the same strings against the
    same meta, because the CLIP branch of the widened notice is byte-for-byte T218's text. A
    rename that preserves every assertion is not a weakening of a predecessor's pins; keeping
    a caller-less alias to avoid the rename would have been the fork this repo has a lesson
    about, and check_wiring blocked the commit that tried it.
    """
    from core.comm.ask import build_context, unusable_evidence_notice

    _ctx, meta = build_context(["core/comm/bus.py"], root=str(REPO))
    assert meta["truncated"] is True
    assert "EVIDENCE CLIPPED" in unusable_evidence_notice(meta)
