"""Pins for the pointer-promise census (scripts/checkers/check_pointer_promises.py).

WHY THIS EXISTS
---------------
On 2026-07-25 the public README was found citing `research/reviewed/` five times as
"the verdicts, preserved verbatim -- ~180 records". That directory held 51 files of raw
April session JSONL and drill JSON: zero verdicts. The records had moved to
docs/library/report/ in f8510b6, which re-pointed every FILE reference -- but a DIRECTORY
reference does not 404 when its contents move, so it survived and kept rendering as a
working link.

All 31 local links on that page resolved. Zero dead. **A link checker gives a clean bill of
health to exactly this rot**, because it verifies RESOLVABILITY and the rot is in CONTENTS.
(lesson: link_checker_blind_to_moved_contents)

DESIGN, reconciled from a fenced two-seat round (deepseek mechanism / kimi adversarial):

  deepseek's first design verified whether a claim held SOMEWHERE IN THE REPO. Its own pin
  P6 admitted that passes the FSQ.md case -- "evidence exists" is true, just not where the
  link points -- i.e. it would not catch the defect it was built for. Fixed here by
  asserting on the LINK TARGET's contents, never the repo globally.

  kimi's adversarial half named four failure modes. Three are answered in this design:
    FM1 "one compliant file re-silences the guard"  -> assert a PROPORTION of the claimed
        cardinal, not mere presence. One stray .md cannot restore green.
    FM3 "the promise vocabulary will false-positive on Daniel's own prose, and the first
        time it blocks him it is dead"               -> this is a REPORT, never a CI gate.
        It always exits 0. It cannot block anyone.
    FM-scope "it would flag the 230 immutable library projections that were true when
        written"                                     -> scoped to live surfaces only.
  FM2 ("blind to right-class-wrong-instance") is NOT solved and is not claimed to be.

Per docs/method-baseline-2026-07.md, these pins commit BEFORE the code they gate.
"""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# NOT importorskip. A pin that SKIPS when its subject is missing reads as green and is
# exactly the fails-open genus this checker exists to catch (see the door-parity parser:
# 0 verbs seen, 66 phantom passes). These fail loudly until the checker lands.
from scripts.checkers import check_pointer_promises as cpp  # noqa: E402


def _doc(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# --------------------------------------------------------------------------
# P1 -- the README rot itself. The defining case.
# --------------------------------------------------------------------------
def test_p1_detects_the_readme_rot(tmp_path):
    """Prose promises ~180 records; the linked target holds none of that class."""
    target = tmp_path / "research" / "reviewed"
    target.mkdir(parents=True)
    (target / "rb25-drill3-evidence.json").write_text("{}", encoding="utf-8")
    (target / "rb25-drill4-soak.json").write_text("{}", encoding="utf-8")

    doc = _doc(
        tmp_path,
        "README.md",
        "The verdicts are preserved verbatim in "
        "[`research/reviewed/`](research/reviewed/) -- ~180 records; you can read "
        "every disagreement and who turned out to be right.",
    )

    findings = cpp.scan_doc(doc, root=tmp_path)
    mismatches = [f for f in findings if f.verdict == "MISMATCH"]
    assert mismatches, f"expected a MISMATCH, got {findings!r}"
    m = mismatches[0]
    assert m.claimed == 180
    assert m.observed == 0
    assert "research/reviewed" in m.target


# --------------------------------------------------------------------------
# P2 -- a true claim on a correct target must stay silent.
# --------------------------------------------------------------------------
def test_p2_passes_on_a_correct_claim(tmp_path):
    target = tmp_path / "docs" / "library" / "report"
    target.mkdir(parents=True)
    for i in range(114):
        (target / f"20260721_review-{i}.md").write_text("# review", encoding="utf-8")

    doc = _doc(
        tmp_path,
        "README.md",
        "114 review and verification records live in "
        "[`docs/library/report/`](docs/library/report/).",
    )

    findings = cpp.scan_doc(doc, root=tmp_path)
    assert not [f for f in findings if f.verdict == "MISMATCH"], f"false positive: {findings!r}"


# --------------------------------------------------------------------------
# P3 -- kimi FM1: one compliant file must NOT restore green.
# --------------------------------------------------------------------------
def test_p3_one_compliant_file_does_not_resilence(tmp_path):
    """The guard's pass-signal must not be as fragile as the rot it hunts."""
    target = tmp_path / "research" / "reviewed"
    target.mkdir(parents=True)
    (target / "20260721_one-real-verdict.md").write_text("# verdict", encoding="utf-8")
    for i in range(50):
        (target / f"drill-{i}.json").write_text("{}", encoding="utf-8")

    doc = _doc(
        tmp_path,
        "README.md",
        "The verdicts are preserved verbatim in "
        "[`research/reviewed/`](research/reviewed/) -- ~180 records.",
    )

    findings = cpp.scan_doc(doc, root=tmp_path)
    assert [f for f in findings if f.verdict == "MISMATCH"], (
        "one stray matching file silenced the census -- kimi FM1 regression"
    )


# --------------------------------------------------------------------------
# P4 -- a claim with no cardinal cannot be falsified; stay quiet.
# --------------------------------------------------------------------------
def test_p4_no_cardinal_is_not_a_mismatch(tmp_path):
    target = tmp_path / "research" / "reviewed"
    target.mkdir(parents=True)
    (target / "whatever.json").write_text("{}", encoding="utf-8")

    doc = _doc(
        tmp_path,
        "README.md",
        "See the files in [`research/reviewed/`](research/reviewed/) for more information.",
    )

    findings = cpp.scan_doc(doc, root=tmp_path)
    assert not [f for f in findings if f.verdict == "MISMATCH"]


# --------------------------------------------------------------------------
# P5 -- a pointer at a target that does not exist is a different defect,
#       and must be reported distinctly rather than silently swallowed.
# --------------------------------------------------------------------------
def test_p5_missing_target_reports_unverifiable_not_pass(tmp_path):
    doc = _doc(
        tmp_path,
        "README.md",
        "The verdicts are in [`research/gone/`](research/gone/) -- ~180 records.",
    )
    findings = cpp.scan_doc(doc, root=tmp_path)
    assert any(f.verdict == "UNVERIFIABLE" for f in findings), (
        "a vanished target must fail LOUD, not pass silently (the fails-open genus)"
    )


# --------------------------------------------------------------------------
# P6 -- kimi FM3 / the principal bar: this is a REPORT. It never blocks.
# --------------------------------------------------------------------------
def test_p6_census_always_exits_zero_even_with_findings(tmp_path):
    """A guard that cries wolf on Daniel's own prose is dead, and takes the idea with it."""
    target = tmp_path / "research" / "reviewed"
    target.mkdir(parents=True)
    (target / "drill.json").write_text("{}", encoding="utf-8")
    _doc(
        tmp_path,
        "README.md",
        "The verdicts are in [`research/reviewed/`](research/reviewed/) -- ~180 records.",
    )

    exit_code = cpp.run_census(root=tmp_path, live_docs=["README.md"])
    assert exit_code == 0, "the census must never block a commit -- it reports, it does not gate"


# --------------------------------------------------------------------------
# P7 -- scope: immutable library projections were true when written.
# --------------------------------------------------------------------------
def test_p8_ok_line_cannot_claim_clean_when_nothing_was_examined(tmp_path):
    """kimi PATH 1: '0 flagged' must be distinguishable from '0 examined'.

    The first draft printed "[OK] every falsifiable directory promise matches" whenever
    nothing was flagged -- which reads identically for a doc full of unfalsifiable pointers
    and for a doc that was never really checked. That is the fails-open genus, shipped
    inside the checker built to catch it. deepseek asserted the caller distinguished these;
    it did not. The census must report what it EXAMINED, not only what it found.
    """
    (tmp_path / "docs").mkdir()
    _doc(tmp_path, "EMPTY.md", "No links here at all.")

    stats = cpp.census_stats(root=tmp_path, live_docs=["EMPTY.md"])
    assert stats["examined"] == 0
    assert stats["flagged"] == 0
    assert stats["clean_claim"] is False, (
        "with nothing examined the census must NOT assert everything matches"
    )


def test_p9_cardinal_binds_to_the_nearest_promise_not_the_first(tmp_path):
    """kimi PATH 2 / deepseek (b): first-cardinal-wins is a constructible false positive."""
    target = tmp_path / "research" / "reviewed"
    target.mkdir(parents=True)
    for i in range(200):
        (target / f"verdict-{i}.md").write_text("# v", encoding="utf-8")

    doc = _doc(
        tmp_path,
        "README.md",
        "We tried 3 reports before settling. The verdicts are preserved in "
        "[`research/reviewed/`](research/reviewed/) -- ~180 records.",
    )

    findings = cpp.scan_doc(doc, root=tmp_path)
    mismatches = [f for f in findings if f.verdict == "MISMATCH"]
    assert not mismatches, (
        f"bound the far cardinal '3 reports' instead of the near '~180 records': {findings!r}"
    )
    assert any(f.claimed == 180 for f in findings), f"expected claimed=180, got {findings!r}"


def test_p9b_cardinal_preceding_the_pointer_is_still_bound(tmp_path):
    """Regression: a forward-only window dropped every leading claim.

    Coverage on the live repo fell from 2 falsifiable promises to 0 and the census said
    NOTHING CHECKED -- the honesty line from P8 catching a defect in the fix for P9.
    """
    target = tmp_path / "docs" / "library" / "report"
    target.mkdir(parents=True)
    (target / "only-one.md").write_text("# r", encoding="utf-8")

    doc = _doc(
        tmp_path,
        "README.md",
        "114 review and verification records live in "
        "[`docs/library/report/`](docs/library/report/), with the design rounds elsewhere.",
    )

    findings = cpp.scan_doc(doc, root=tmp_path)
    assert any(f.claimed == 114 for f in findings), (
        f"a cardinal PRECEDING its pointer was dropped: {findings!r}"
    )
    assert any(f.verdict == "MISMATCH" for f in findings)


def test_p10_stray_readme_does_not_inflate_observed(tmp_path):
    """kimi (c): _count_class counted ANY .md, so a directory's own README masked the rot."""
    target = tmp_path / "research" / "reviewed"
    target.mkdir(parents=True)
    (target / "README.md").write_text("# index", encoding="utf-8")
    for i in range(50):
        (target / f"drill-{i}.json").write_text("{}", encoding="utf-8")

    doc = _doc(
        tmp_path,
        "README.md",
        "The verdicts are in [`research/reviewed/`](research/reviewed/) -- 3 records.",
    )

    findings = cpp.scan_doc(doc, root=tmp_path)
    assert [f for f in findings if f.verdict == "MISMATCH"], (
        "a directory's own README.md was counted as a promised record"
    )


def test_p11_markdown_link_with_title_is_not_silently_skipped(tmp_path):
    """deepseek: `[text](url "title")` broke the href parse and vanished from the census."""
    target = tmp_path / "research" / "reviewed"
    target.mkdir(parents=True)
    (target / "drill.json").write_text("{}", encoding="utf-8")

    doc = _doc(
        tmp_path,
        "README.md",
        'The verdicts are in [reviewed](research/reviewed/ "the record") -- ~180 records.',
    )

    findings = cpp.scan_doc(doc, root=tmp_path)
    assert findings, "a titled markdown link was silently skipped"
    assert any(f.verdict == "MISMATCH" for f in findings)


def test_p7_immutable_library_projections_are_out_of_scope(tmp_path):
    lib = tmp_path / "docs" / "library" / "report"
    lib.mkdir(parents=True)
    _doc(
        lib,
        "20260701_historical-record.md",
        "The verdicts are in [`research/reviewed/`](research/reviewed/) -- ~180 records.",
    )
    (tmp_path / "research" / "reviewed").mkdir(parents=True)

    scoped = cpp.live_surfaces(root=tmp_path)
    assert not any("docs/library/" in s.replace("\\", "/") for s in scoped), (
        "history must not be scanned -- corrections supersede, they never delete"
    )
