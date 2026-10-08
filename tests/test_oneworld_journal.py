"""W0 pins -- the one-world UI core's authored journal (spec: atom d622ac, H9).

The contract, modeled on core/eye/routes.py's authored/derived discipline:
- authored facts live in an append-only, tracked journal;
- a fact id is a content hash, so a crash-redelivered or double-written fact is the SAME line
  (idempotency, routes.py P2);
- replay() rebuilds the projection from the journal, so wiping any derived surface loses nothing
  authored (routes.py P5);
- replay is HONEST about drops: a corrupt line is counted as `unparsed`, never silently discarded
  (the found-vs-taken / a_report_that_counts_survivors rule).

Each test repoints JOURNAL_PATH to a tmp file so the real state/world plane never grows under a run
(build-beside-a-neighbour: copy its guards -- routes.py's tests monkeypatch the module path).
"""
from __future__ import annotations

import json

import pytest

journal = pytest.importorskip("core.oneworld.journal")


@pytest.fixture
def jp(tmp_path, monkeypatch):
    p = tmp_path / "world.jsonl"
    monkeypatch.setattr(journal, "JOURNAL_PATH", p)
    return p


def test_append_then_replay_preserves_order(jp):
    a = journal.append("mode_set", "claude", {"surface": "fleet", "mode": "quiet"})
    b = journal.append("hail", "daniil", {"text": "walk day?"})
    assert a.startswith("wf_") and b.startswith("wf_")
    facts = journal.replay()["facts"]
    assert [f["id"] for f in facts] == [a, b]
    assert facts[0]["kind"] == "mode_set" and facts[0]["actor"] == "claude"
    assert facts[0]["payload"]["surface"] == "fleet"
    # every authored field the projection could need is carried on the record itself (T335).
    for f in facts:
        assert set(f) >= {"id", "kind", "actor", "payload", "at", "session_id"}


def test_same_content_is_one_fact(jp):
    """Idempotency: the content hash makes a double-write the same line and the same fact."""
    first = journal.append("mode_set", "claude", {"surface": "fleet", "mode": "quiet"})
    again = journal.append("mode_set", "claude", {"surface": "fleet", "mode": "quiet"})
    assert first == again
    assert jp.read_text(encoding="utf-8").strip().count("\n") == 0  # one line, no trailing dupe
    assert journal.replay()["taken"] == 1


def test_distinct_appends_both_land(jp):
    """rows-in == rows-out: the silent-overwrite class. Two distinct facts must both survive."""
    ids = {journal.append("ev", "a", {"n": i}) for i in range(5)}
    assert len(ids) == 5
    r = journal.replay()
    assert r["taken"] == 5
    assert {f["id"] for f in r["facts"]} == ids


def test_replay_rebuilds_from_journal_alone(jp):
    """The drift test: a cold reader replaying the journal sees exactly the authored history --
    no in-process state, no projection, needed. Wiping any derived surface loses nothing."""
    want = [journal.append("ev", "a", {"n": i}) for i in range(3)]
    # Re-import-free cold read: replay() reads the file, not any cached state.
    facts = journal.replay()["facts"]
    assert [f["id"] for f in facts] == want


def test_corrupt_line_is_counted_not_silently_dropped(jp):
    """found-vs-taken: a garbage journal line must be reported as unparsed and must NOT reduce the
    real count silently -- the tautology this house keeps paying for (a_report_that_counts_survivors)."""
    good = journal.append("ev", "a", {"n": 1})
    with open(jp, "a", encoding="utf-8") as f:
        f.write("{ this is not json\n")
    good2 = journal.append("ev", "a", {"n": 2})
    r = journal.replay()
    assert r["taken"] == 2
    assert r["unparsed"] == 1
    assert [f["id"] for f in r["facts"]] == [good, good2]


def test_empty_journal_is_clean_zero_not_an_error(jp):
    r = journal.replay()
    assert r == {"facts": [], "taken": 0, "unparsed": 0} or (
        r["facts"] == [] and r["taken"] == 0 and r["unparsed"] == 0)
