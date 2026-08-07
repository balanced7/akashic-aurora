"""
T214 -- vocabulary as a comparable set: the W133 instrument. RED first.

W133 (filed tonight, the oldest wish in the repo -- restated every ~2 weeks since
2026-06-19) asks for a guard on forked semantics: one CONCEPT implemented by several
mechanisms that quietly disagree. W134 corrected the premise -- the naming guard EXISTS
(check_boundaries: no-duplicate-class-names, no-duplicate-module-basename) and works. It
catches HOMONYMS: two things sharing one identifier, which is greppable.

None of tonight's four violations were homonyms:
    drained    three different cursor keys, no shared token
    unread     _unread_count vs the consume door
    wakeable   NOT AN IDENTIFIER ANYWHERE -- it lives only in prose and reasoning
    fixed      one identifier, one definition, two unshared assumptions

So the extractor cannot read identifiers. It must read what the codebase TALKS ABOUT --
comments and docstrings -- because that is where a concept lives before it has a name.

WHAT THIS IS AND IS NOT. It produces CANDIDATES, never violations. Most undefined words
are perfectly fine (`the`, `buffer`, `retry`); a concept discussed across many files with
no LEXICON entry is merely worth a look. This is the cheap wide tier: the index proposes,
and the fan disposes. Claiming a violation here would be the confident-inference failure
this whole arc has been about.

SPREAD IS THE SIGNAL, NOT FREQUENCY. A word used two hundred times in one module is
that module's local jargon and fine. A word used in six DIFFERENT files is a shared
concept -- and a shared concept with no single definition is exactly how `drained` came
to mean three things.

Run: py -m pytest tests/test_t214_terms_domain.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import terms as TM  # noqa: E402


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "a.py").write_text(
        '"""The cursor is drained when the consumer advances past it."""\n'
        "def f():\n    # a drained lane is not the same as an empty lane\n    pass\n",
        encoding="utf-8")
    (tmp_path / "b.py").write_text(
        '"""Wakeable seats beat their key; a drained lane looks wakeable."""\n'
        "x = 1  # drained\n", encoding="utf-8")
    (tmp_path / "c.py").write_text(
        "# the lane is drained by the sweep\ny = 2\n", encoding="utf-8")
    return tmp_path


def test_terms_come_from_prose_not_identifiers(tree):
    """The whole reason this exists: 'wakeable' is not an identifier anywhere in the
    real repo, and it cost six turns. An identifier-only extractor cannot see it."""
    got = TM.extract(root=str(tree), min_files=1)
    assert "drained" in got
    assert "wakeable" in got


def test_spread_is_measured_in_FILES_not_occurrences(tree):
    """A word used 200 times in one module is local jargon. A word in six different
    files is a shared concept -- and a shared concept with no definition is how
    'drained' came to mean three things."""
    got = TM.extract(root=str(tree), min_files=1)
    assert got["drained"]["files"] == 3
    assert got["wakeable"]["files"] == 1


def test_min_files_filters_local_jargon(tree):
    got = TM.extract(root=str(tree), min_files=3)
    assert "drained" in got
    assert "wakeable" not in got, "single-file words are local, not shared vocabulary"


def test_stopwords_and_code_noise_are_dropped(tree):
    (tree / "d.py").write_text(
        "# the return value should be a string that we return for the caller\n"
        "# self param kwargs args None True False\n", encoding="utf-8")
    got = TM.extract(root=str(tree), min_files=1)
    for noise in ("the", "return", "value", "self", "none", "true", "string"):
        assert noise not in got, f"{noise} is noise, not vocabulary"


def test_lexicon_terms_are_read_from_the_lexicon(tmp_path):
    lex = tmp_path / "LEXICON.md"
    lex.write_text("# Lexicon\n\n## Drained\nthe cursor advanced.\n\n"
                   "### `worklive`\na heartbeat key.\n\n"
                   "**Attendance** -- the verdict.\n", encoding="utf-8")
    got = TM.lexicon_terms(path=str(lex))
    assert {"drained", "worklive", "attendance"} <= got


def test_the_domains_register_and_share_a_key_type():
    from core.coord import compare as CMP
    assert "terms:code" in CMP.DOMAINS and "terms:lexicon" in CMP.DOMAINS
    assert CMP.DOMAINS["terms:code"][1] == CMP.DOMAINS["terms:lexicon"][1]


def test_the_result_is_labelled_candidates_never_violations():
    """A word with no LEXICON entry is worth a LOOK, not an accusation. Most undefined
    words are fine. Claiming a violation here would be the confident-inference failure
    this whole arc has been about."""
    blind = " ".join(TM.BLIND).lower()
    assert "candidate" in blind
    assert "not a violation" in blind or "never a violation" in blind


def test_blindness_is_named(tree):
    """Heuristic extraction that does not confess its heuristics gets read as a census."""
    assert TM.BLIND and len(TM.BLIND) >= 3


def test_the_known_positives_are_recorded_as_a_calibration_set():
    """Four terms MEASURABLY forked and cost real turns. They are this module's ground
    truth, so the next scoring idea gets a verdict instead of a vibe."""
    assert set(TM.KNOWN_FORKED) == {"drained", "unread", "wakeable", "fixed"}


def test_the_measured_failure_of_the_ranking_is_recorded():
    """THE MOST IMPORTANT PIN HERE. Ranking by rarity x subsystem-spread was calibrated
    against the four known positives and FAILED -- they landed at the 71st, 94th, 76th
    and 13th percentile, three of four in the bottom quartile, so the score is
    anti-correlated with truth.

    A negative result that is not written down gets re-discovered by the next person who
    has the same reasonable idea. This pin makes deleting the confession a test failure."""
    blind = " ".join(TM.BLIND).lower()
    assert "negative result" in blind
    assert "anti-correlated" in blind


def test_the_blind_list_does_not_claim_high_spread_is_safe():
    """CAUGHT BY THE NEXT SEAT within an hour of inheriting this file, and the error was
    mine. BLIND[1] used to explain the measurement with a causal story -- "high spread
    means the meaning got socialised" -- filed in the same list as the measurement with
    nothing marking which was measured and which was invented.

    My OWN headline finding the same day falsifies it: W135 records `open` as forked
    across 61 files and 13 subsystems, the highest-spread term in the repo. The harm is
    specific and inheritable: a reader concludes spread is safe and skips exactly the
    word most worth checking.

    An inference shelved beside a measurement, undifferentiated, is the plane-laundering
    the 07-30 relationship design forbids. This pin makes the correction non-revertible."""
    blind = " ".join(TM.BLIND).lower()
    assert "mechanism is unknown" in blind
    assert "falsified" in blind and "61 files" in blind
    assert "selection bias" in blind, "the calibration set is survivors-of-pain, not a sample"
    assert "socialised" not in blind or "falsified" in blind


def test_scoring_is_still_exercised_so_a_future_fix_is_measurable(tree):
    """The score stays computed -- the calibration set is only useful if the number it
    grades still exists."""
    got = TM.extract(root=str(tree), min_files=1)
    assert "score" in got["drained"] and "dirs" in got["drained"]
    # The IDF property, stated as the test rather than assumed: a word in EVERY file
    # carries no information and scores 0, while a rarer word outranks it. (drained is in
    # all 3 fixture files; wakeable in 1.) My first assertion here demanded drained > 0
    # and was wrong -- the metric was right and the expectation was not, which is worth
    # keeping visible given this module's whole lesson is about trusting measurements
    # over intuitions.
    assert got["drained"]["score"] == 0.0, "a term in every file has zero IDF"
    assert got["wakeable"]["score"] > got["drained"]["score"]


def test_extraction_survives_an_unreadable_file(tree, monkeypatch):
    bad = tree / "bad.py"
    bad.write_bytes(b"\xff\xfe not valid utf-8 \x00")
    got = TM.extract(root=str(tree), min_files=1)
    assert "drained" in got, "one bad file must not cost the scan"
