"""T278 S7: the directive watcher -- the organ finally closes its own founding wound.

THE EYE was built because directives died in the transcript plane. It made them FINDABLE.
Findable-if-someone-thinks-to-look is not the same as SURFACED: on 2026-08-11 it turned up
"remember to fan out so you dont get bogged down in the mechanics" -- said twice, across two
sessions, never actioned -- and it was found by accident, while chasing an unrelated defect
in `freq`. Nobody was looking. Nobody would have. This slice is the looking.

WHAT IT DOES, mechanically and with no LLM anywhere in the path (the organ's standing law):
mine the OPERATOR axis for phrases that recur, collapse records to utterances, drop
boilerplate by document frequency, then ask of each survivor -- does ANY durable plane cite
this? The ledger, a lesson, an atom, a commit. A phrase he has said three times across two
sessions that nothing durable references is the exact shape of a directive that evaporated.

THE TWO PINS THAT MATTER MOST ARE THE ONES THAT KEEP IT QUIET:

  P5 -- when everything recurring HAS been acted on, it reports nothing, affirmatively.
        The empty case has to be trustworthy before the populated one is worth anything,
        because silence is the state this thing will be in almost every day.
  P6 -- a hard cap. Today a wedge page fired on a healthy seat and kimi's own note said it
        plainly: a page that fires on healthy seats trains us to ignore pages. A watcher
        that surfaces twelve maybes each morning is scrolled past within a week, and THEN
        its silence reads as all-clear while it is actually being ignored. High precision,
        few items, or it is worse than nothing.

And P7: it proposes, never ratifies. It files no tasks. Four independent arrivals in this
house have landed on `instrument_proposes_never_self_ratifies`; this one inherits it rather
than rediscovering it.

Fixture truth (session_watch_a / session_watch_b):
  "always fence the migration path before shipping it" -- operator in BOTH sessions
      (plus an agent echo in each, and a duplicate queue-op record in b). UNCITED.
  "make the harvest ledger visible on every boot"      -- operator in BOTH sessions. CITED
      by a durable artifact in the pins that supply one.
  "lets keep building the thing"                       -- operator in both, but BOILERPLATE.

Run: py -m pytest tests/test_t278_s7_directive_watcher.py -q
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.eye import directives as DIR  # noqa: E402
from core.eye import index as EYE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "eye"

FENCE = "always fence the migration path before shipping it"
HARVEST = "make the harvest ledger visible on every boot"


@pytest.fixture()
def db(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for f in ("session_watch_a.jsonl", "session_watch_b.jsonl"):
        shutil.copy(FIX / f, corpus / f)
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=dbp)
    return dbp


def _phrases(items):
    return " || ".join(i["phrase"] for i in items)


# ---------------------------------------------------------------- P1: it finds one
def test_p1_a_recurring_uncited_directive_is_surfaced(db):
    """The founding case, reproduced: said across two sessions, nothing durable cites it."""
    rep = DIR.unheeded(db_path=db, durable_texts=["some unrelated task about caching"])
    assert rep["items"], "the watcher found nothing in a corpus that contains the case"
    top = rep["items"][0]
    assert "fence the migration path" in top["phrase"]
    assert top["sessions"] >= 2 and top["utterances"] >= 2
    assert top["cited"] is False


def test_p1b_every_item_carries_addresses_that_resolve(db):
    """A claim about his voice that cannot be checked is a claim to distrust. Each item
    carries event addresses, and each address resolves to the verbatim record."""
    rep = DIR.unheeded(db_path=db, durable_texts=[])
    for item in rep["items"]:
        assert item["refs"], "no refs = an unfalsifiable assertion about what he said"
        for ref in item["refs"]:
            ev = EYE.get_event(ref, db_path=db)
            assert ev is not None and ev["voice"] == "operator"
            assert item["phrase"] in " ".join(ev["text"].lower().split())


# ---------------------------------------------------------------- P2: the loop closes
def test_p2_once_a_durable_plane_cites_it_it_stops_being_reported(db):
    """THE point of the whole organ. A directive that became work must go quiet, or the
    watcher is just a nag that never acknowledges being obeyed."""
    before = DIR.unheeded(db_path=db, durable_texts=[])
    assert FENCE in _phrases(before["items"]) or "fence the migration path" in _phrases(before["items"])

    after = DIR.unheeded(db_path=db, durable_texts=[
        "T301: always fence the migration path before shipping it -- shipped @abc123"])
    assert "fence the migration path" not in _phrases(after["items"]), (
        "the ledger cites it now; the watcher must fall silent about it")


def test_p2b_citation_matching_is_not_fooled_by_a_single_shared_word(db):
    """'migration' appearing somewhere in the ledger is NOT evidence the directive was
    heard. A loose match would silence the watcher for free, which is the failure mode
    that leaves a directive dead while the instrument reports all-clear."""
    rep = DIR.unheeded(db_path=db, durable_texts=["T999: a migration of the docs folder"])
    assert "fence the migration path" in _phrases(rep["items"])


# ---------------------------------------------------------------- P3: boilerplate
def test_p3_boilerplate_is_not_a_directive(db):
    """'lets keep building the thing' recurs exactly as often as the real directive and
    means nothing. Document frequency is the mechanical discriminator; without it the
    watcher drowns in conversational filler."""
    rep = DIR.unheeded(db_path=db, durable_texts=[])
    assert "keep building" not in _phrases(rep["items"])


# ---------------------------------------------------------------- P4: the operator axis
def test_p4_agent_echoes_and_duplicate_records_never_inflate_the_count(db):
    """Both fixtures echo the directive back in the agent's voice, and session b records
    the operator's line TWICE (queue-op + user). The count is HIS utterances."""
    rep = DIR.unheeded(db_path=db, durable_texts=[])
    top = [i for i in rep["items"] if "fence the migration path" in i["phrase"]][0]
    assert top["utterances"] == 2, (
        "two sessions, one utterance each -- not 4 records, not 2 echoes")
    assert top["sessions"] == 2


# ---------------------------------------------------------------- P5: SILENCE WORKS
def test_p5_when_everything_recurring_is_cited_it_reports_nothing_affirmatively(db):
    """The state this thing is in almost every day. It must be trustworthy BEFORE the
    populated case is worth anything -- and it must SAY it looked, not just return []."""
    rep = DIR.unheeded(db_path=db, durable_texts=[
        "always fence the migration path before shipping it",
        "make the harvest ledger visible on every boot",
    ])
    assert rep["items"] == []
    assert rep["checked"] > 0, "it must report HOW MANY candidates it examined"
    assert rep["clear"] is True, "an affirmative all-clear, distinguishable from a crash"


# ---------------------------------------------------------------- P6: the wolf guard
def test_p6_the_report_is_hard_capped(db):
    """A page that fires on healthy seats trains us to ignore pages (kimi, 2026-08-11)."""
    rep = DIR.unheeded(db_path=db, durable_texts=[], limit=1)
    assert len(rep["items"]) <= 1
    assert rep["withheld"] >= 0, "what was cut is COUNTED -- a silent truncation reads as "
    if rep["withheld"]:
        assert rep["items"], "withholding implies something was shown"


def test_p6b_ranking_puts_the_strongest_evidence_first(db):
    """With a cap, ORDER is the whole product: the one item shown must be the best one."""
    rep = DIR.unheeded(db_path=db, durable_texts=[], limit=1)
    assert "fence the migration path" in rep["items"][0]["phrase"], (
        "the directive he repeated across sessions outranks the one-session case")


# ---------------------------------------------------------------- P7: no self-ratifying
def test_p7_the_watcher_has_no_write_path(db):
    """It surfaces; the human decides. Four independent arrivals in this house landed on
    instrument_proposes_never_self_ratifies -- inherited, not rediscovered."""
    import inspect
    src = inspect.getsource(DIR)
    for forbidden in ("task_ledger", "def learn", "subprocess", "conductor",
                      "def propose", "git commit"):
        assert forbidden not in src, f"the watcher must not be able to act: found {forbidden!r}"
