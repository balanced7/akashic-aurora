"""T313 RED pins -- the indexer and the archiver must share ONE corpus definition.

THE MEASURED DEFECT, 2026-08-16:
    state/eye/recovered            12 files   <- what THE EYE reads as "the rescued archive"
    E:\\Akashic Aurora\\transcripts\\rolling  102 files   <- what archive_transcripts.py WRITES
    in both: 12 · archive-only: 90

Ninety archived sessions the indexer cannot see. And this is not an oversight anyone was casual
about -- core/eye/index.py's own docstring for default_corpus() says:

    "Transcripts rotate off the harness disk, and a rebuild that reads only the live directory
     silently drops every rescued session -- which is exactly what happened twice on 2026-08-11,
     the second time to the very sessions recovered from a shadow copy hours earlier."

So the author fought this bug, built a rescue path, and pointed it at a directory holding 12 of
the 102 files. Two archives, neither aware of the other -- the same shape as the two divergent
directive-register copies and the two dependency stores. The fix is not "add another path"; it is
ONE declaration that the writer and the reader both read, plus a pin that fails when they drift.

Pin 5 is the one that matters longest: a corpus that does not publish its own coverage cannot
tell you it has shrunk. Lesson: a_coverage_contract_must_state_the_scope_it_globs_not_just_the
_files_it_read -- whose own example is THE EYE printing "83/83 manifest_complete" while globbing
one level and seeing 82 of 443 transcripts on disk.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config_declares_the_archive_roots_once():
    """One home for the constant. Two literals in two modules IS the defect."""
    import config
    roots = getattr(config, "TRANSCRIPT_ARCHIVE_ROOTS", None)
    assert roots, ("config.TRANSCRIPT_ARCHIVE_ROOTS does not exist -- the archive roots are still "
                   "a literal inside scripts/ops/archive_transcripts.py, which is why the indexer "
                   "could point somewhere else and nobody noticed")
    assert any("rolling" in str(r).lower() for r in roots), \
        f"the rolling archive must be among the declared roots, got {roots}"


def test_archiver_and_indexer_read_the_same_constant():
    """The writer of the archive and its reader must not be able to disagree.

    This is the pin that outlives the fix: it fails the day someone adds a destination to one
    side only, which is exactly how the 90-file gap opened."""
    import config
    from scripts.ops import archive_transcripts as arch
    declared = {str(Path(r)).rstrip("\\/").lower() for r in config.TRANSCRIPT_ARCHIVE_ROOTS}
    writing = {str(Path(d)).rstrip("\\/").lower() for d in arch.DEFAULT_DESTS}
    assert writing <= declared, (
        f"archive_transcripts writes to destinations the shared constant does not declare: "
        f"{writing - declared}. The reader will never see them.")


def test_default_corpus_includes_the_rolling_archive():
    """The 90 archive-only sessions must become visible to ingest."""
    import config
    from core.eye.index import default_corpus
    roots = [Path(r) for r in config.TRANSCRIPT_ARCHIVE_ROOTS if Path(r).is_dir()]
    if not roots:
        import pytest
        pytest.skip("no archive root present on this machine")
    archived = {p.name for r in roots for p in r.glob("*.jsonl")}
    seen = {p.name for p in default_corpus()}
    missing = archived - seen
    assert not missing, (
        f"{len(missing)} archived session(s) are invisible to default_corpus(), "
        f"e.g. {sorted(missing)[:5]}. The archive exists precisely because these rotated off "
        "the harness disk -- if the indexer cannot read them they are unreachable everywhere.")


def test_default_corpus_publishes_its_coverage():
    """A corpus that cannot state what it scanned cannot report that it shrank.

    Absence of a file must be a VISIBLE number, not a smaller silent result."""
    try:
        from core.eye.index import corpus_coverage
    except ImportError as e:
        raise AssertionError(
            f"core.eye.index.corpus_coverage() does not exist ({e}) -- default_corpus() returns a "
            "bare list, so a root that vanishes or a glob that narrows produces a smaller answer "
            "with no signal. Publish roots scanned and per-root counts.")
    cov = corpus_coverage()
    assert isinstance(cov, dict) and cov.get("roots"), \
        f"coverage must name the roots it scanned, got {cov!r}"
    for r in cov["roots"]:
        assert "path" in r and "files" in r, f"each root reports path + files, got {r!r}"
    assert "total" in cov, "coverage must carry a total"


def test_projects_glob_reaches_nested_transcripts():
    """Second-order defect, same family: the live glob is one level deep.

    `for d in root.iterdir() if d.is_dir() for p in d.glob('*.jsonl')` cannot see a transcript in
    projects/<x>/subagents/. The recorded instance of this class is THE EYE reporting
    '83/83 manifest_complete' while seeing 82 of 443 files on disk."""
    from core.eye.index import default_corpus, corpus_coverage
    live = Path.home() / ".claude" / "projects"
    if not live.is_dir():
        import pytest
        pytest.skip("no live projects directory on this machine")
    nested = [p for p in live.rglob("*.jsonl") if p.parent.parent != live]
    if not nested:
        import pytest
        pytest.skip("no nested transcripts exist to find")
    seen = {p.name for p in default_corpus()}
    missing = [p for p in nested if p.name not in seen]
    assert not missing, (
        f"{len(missing)} nested transcript(s) are invisible to default_corpus(), e.g. "
        f"{[str(p.relative_to(live)) for p in missing[:3]]} -- a one-level glob cannot reach "
        "projects/<id>/subagents/, where every research agent's findings live")
    cov = corpus_coverage()
    assert "subagent_transcripts" in cov, (
        "nested subagent transcripts must be COUNTED separately, not silently mixed in: ~5x more "
        "of them exist than operator sessions, and an unlabelled mix makes a terse operator "
        "look verbose")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"  FAIL  {name}\n        {str(e)[:300]}")
            except Exception as e:
                failures += 1
                print(f"  ERROR {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"\n{failures} failing pin(s) -- RED is expected before T313 is built.")
    sys.exit(1 if failures else 0)
