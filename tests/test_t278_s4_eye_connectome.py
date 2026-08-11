"""T278 S4: the connectome -- edges with formation metadata, and `eye trace`.

WHY THIS SLICE EXISTS, measured before it was written (2026-08-11, live corpus, 8 sessions):

  - the transcript's native causal chain is `uuid` -> `parentUuid`. Coverage by record type:
    assistant 3629/3629, user 1913/1913, system 144/144, attachment 1299/1299 -- and
    queue-operation 0/398. The chain is complete everywhere EXCEPT the record class where
    the operator's queued voice lives (operator_speech_hides_in_queue_operation_records).
  - bridging queue-op records to their `user` twin by text identity reaches 78.6% of his
    queued utterances (193 exact + 2 contained of 248). The remaining 21.4% have NO twin
    at all -- they exist only in the queue lane, unreachable from any recorded chain.
  - and the same utterance is RECORDED TWICE in that lane (enqueue + dequeue, identical
    text, 1.6-17s apart). S2's pyramid learned this inline; `eye freq` never did, and the
    inflation crosses its own verdict threshold -- the live "fan out / don't get bogged
    down in the mechanics" family reads 4 operator events across 2 sessions
    (STANDING-DIRECTIVE) when it is 2 distinct utterances across 2 sessions (RECURRING).

So the three symptoms are one mechanism: an utterance is a SET of records. This slice
builds that set as a typed edge, and the verdict-inflation fix falls out of the substrate
rather than being point-fixed in `freq`
(convergent_fixes_describe_meaning_not_location_or_membership).

EVIDENCE GRADE is the load-bearing column -- three ways an edge can be known, never mixed:
  recorded  -- the harness wrote the link down    (parentUuid)
  derived   -- we computed it from record content (text identity)
  inferred  -- we guessed it from position        (adjacency; the orphan's only handhold)
A walk that crosses an INFERRED edge sets `degraded` and says so. An inference laundered
as a record is the class this whole organ exists to refuse.

Fixture truth (tests/fixtures/eye/):
  gamma: u1 <- a1 <- u2 <- a2 <- a3 recorded chain (lines 1,2,5,6,9)
         lines 3,4 = one queued utterance recorded twice, twin at line 5 (bridgeable)
         lines 7,8 = one queued utterance recorded twice, NO twin (true orphan)
  delta: d1 <- d2 <- d3 (lines 1,2,5); lines 3,4 = the SAME cross-session phrase, twice

Run: py -m pytest tests/test_t278_s4_eye_connectome.py -q
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.eye import connectome as CONN  # noqa: E402
from core.eye import index as EYE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "eye"

G = "session_gamma"
D = "session_delta"


@pytest.fixture()
def db(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for f in ("session_gamma.jsonl", "session_delta.jsonl"):
        shutil.copy(FIX / f, corpus / f)
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=dbp)
    CONN.build(db_path=dbp)
    return dbp


# ---------------------------------------------------------------- P1: the chain
def test_p1_recorded_chain_walks_upstream_in_order(db):
    """parentUuid becomes a walkable ancestry -- nearest first, no re-search."""
    t = CONN.trace(f"{G}:9", db_path=db)          # a3
    assert [u["event_id"] for u in t["upstream"]] == [
        f"{G}:6", f"{G}:5", f"{G}:2", f"{G}:1"], "a2 <- u2 <- a1 <- u1"
    assert all(u["evidence"] == "recorded" for u in t["upstream"])
    assert t["degraded"] is False, "a purely recorded walk carries no flag"


def test_p1b_downstream_returns_descendants(db):
    t = CONN.trace(f"{G}:1", db_path=db)          # u1, the root
    assert [d["event_id"] for d in t["downstream"]] == [
        f"{G}:2", f"{G}:5", f"{G}:6", f"{G}:9"]
    assert t["upstream"] == [], "the root has no ancestors -- empty, not fabricated"


# ---------------------------------------------------------------- P2: the utterance set
def test_p2_same_utterance_collapses_the_duplicate_pair(db):
    """One utterance, N records. The duplicate queue-op pair AND the user twin are one set."""
    grp = CONN.utterance_group(f"{G}:3", db_path=db)
    assert grp == [f"{G}:3", f"{G}:4", f"{G}:5"], (
        "enqueue + dequeue + the delivered user twin are the SAME utterance")
    # the true orphan pair is a set of two, with no twin to join it
    assert CONN.utterance_group(f"{G}:7", db_path=db) == [f"{G}:7", f"{G}:8"]
    # a plain agent turn is its own singleton -- never grouped by accident
    assert CONN.utterance_group(f"{G}:2", db_path=db) == [f"{G}:2"]


# ---------------------------------------------------------------- P3: the bridge
def test_p3_queued_operator_speech_reaches_the_recorded_chain(db):
    """The 78.6% case: a queue-op record has no uuid, but its twin does -- so his voice
    is reachable from the chain THROUGH the utterance set, not by inference."""
    t = CONN.trace(f"{G}:3", db_path=db)
    assert [u["event_id"] for u in t["upstream"]] == [f"{G}:2", f"{G}:1"], (
        "hops to the twin (line 5), then walks the twin's recorded ancestry")
    bridge = [u for u in t["upstream"] if u["edge_kind"] == "same_utterance"]
    assert bridge == [] and t["bridged_via"] == f"{G}:5", (
        "the bridge is named in the envelope, not smuggled into the ancestor list")
    assert t["degraded"] is False, "text identity is DERIVED, not inferred -- no fog"


# ---------------------------------------------------------------- P4: the orphan
def test_p4_the_true_orphan_is_reachable_and_flagged(db):
    """The 21.4% case. It must NOT be invisible (the founding wound) and must NOT be
    laundered as a recorded link (the founding law). Reachable AND flagged."""
    t = CONN.trace(f"{G}:7", db_path=db)
    assert t["node"]["event_id"] == f"{G}:7", "the orphan resolves at all"
    assert t["upstream"], "an orphan with no handhold at all would be a silent drop"
    assert t["upstream"][0]["evidence"] == "inferred"
    assert t["upstream"][0]["edge_kind"] == "adjacent"
    assert t["upstream"][0]["event_id"] == f"{G}:6", "nearest preceding chained event"
    assert t["degraded"] is True
    assert "inferred" in (t["degraded_reason"] or "").lower()
    assert t["edges_inferred"] >= 1


# ---------------------------------------------------------------- P5: formation metadata
def test_p5_every_edge_this_slice_builds_carries_its_formation(db):
    """Grammar sec 5 + stance atom fa0131: formed_by / formed_at / formed_via on every NEW
    edge. A new edge without them would be indistinguishable from a pre-contract one."""
    edges = CONN.edges(db_path=db)
    assert edges, "the build produced edges"
    for e in edges:
        assert e["formed_by"], f"{e} has no formed_by"
        assert e["formed_at"] is not None, f"{e} has no formed_at"
        assert e["formed_via"] in CONN.FORMED_VIA, f"{e} formed_via out of vocabulary"
        assert e["evidence"] in ("recorded", "derived", "inferred")
    # evidence grade is not free-floating: it is a function of HOW the edge was formed
    grades = {e["formed_via"]: e["evidence"] for e in edges}
    assert grades["transcript"] == "recorded"
    assert grades["text-identity"] == "derived"
    assert grades["adjacency"] == "inferred"


def test_p5b_build_report_is_a_coverage_contract(db):
    rep = CONN.build(db_path=db)
    assert rep["edges_total"] == sum(rep["by_kind"].values())
    assert rep["by_kind"]["follows"] > 0 and rep["by_kind"]["same_utterance"] > 0
    assert rep["by_evidence"]["inferred"] == rep["by_kind"]["adjacent"]
    # rebuild is idempotent -- an edge table that grew on re-run would poison every count
    rep2 = CONN.build(db_path=db)
    assert rep2["edges_total"] == rep["edges_total"]


# ---------------------------------------------------------------- P6: the exclusion trap
def test_p6_pre_contract_edges_are_flagged_never_dropped_never_backfilled(db):
    """Fence r1 C4, the trap this contract was written to avoid: a query FILTERING on
    formation metadata over a pool containing pre-contract edges must say how many it
    could not evaluate. Silence would read as 'none matched'."""
    CONN._insert_pre_contract_edge(f"{G}:9", f"{G}:1", "follows", db_path=db)

    t = CONN.trace(f"{G}:9", db_path=db, formed_via="transcript")
    assert t["pre_contract_edges"] == 1
    assert t["degraded"] is True
    assert "pre-contract" in (t["degraded_reason"] or "").lower()
    assert "1" in (t["degraded_reason"] or ""), "the COUNT is stated, not just the fact"

    # no sentinel backfill -- rewriting history is the fossil class
    raw = [e for e in CONN.edges(db_path=db) if e["formed_via"] is None]
    assert len(raw) == 1 and raw[0]["formed_by"] is None, (
        "the pre-contract edge stays exactly as unlabelled as it was found")


def test_p6b_unfiltered_walk_does_not_flag_pre_contract(db):
    """The flag is about the FILTER, not about the pool. An unfiltered walk evaluates
    nothing and so excludes nothing -- flagging it would train callers to ignore flags."""
    CONN._insert_pre_contract_edge(f"{G}:9", f"{G}:1", "follows", db_path=db)
    t = CONN.trace(f"{G}:9", db_path=db)
    assert t["pre_contract_edges"] == 0 and t["degraded"] is False


# ---------------------------------------------------------------- P7: the verdict flip
def test_p7_freq_counts_distinct_utterances_not_records(db):
    """THE LIVE DEFECT, pinned as a regression. Raw records inflate across the verdict
    threshold; distinct utterances tell the truth. Both numbers ride the envelope --
    the raw count is not hidden, it is labelled."""
    r = EYE.freq(["recurring cross session directive"], db_path=db)
    assert r["operator_records"] == 4, "two sessions x one utterance recorded twice"
    assert r["operator_events"] == 2, "...which is TWO distinct utterances"
    assert r["sessions"] == 2
    assert r["verdict"] == "recurring", (
        "4 records across 2 sessions would read STANDING-DIRECTIVE; 2 utterances do not")


def test_p7b_a_singly_recorded_utterance_is_unaffected(db):
    """The fix must not deflate honest counts -- the twin case is still ONE utterance,
    and a phrase said once stays said once."""
    r = EYE.freq(["gamma queued directive with a twin"], db_path=db)
    assert r["operator_records"] == 3, "enqueue + dequeue + the delivered twin"
    assert r["operator_events"] == 1 and r["sessions"] == 1
    assert r["verdict"] == "mentioned-once"
