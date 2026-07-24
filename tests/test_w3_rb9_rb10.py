"""
Wave 3 / RB-9 + RB-10 -- pre-registered acceptance (committed BEFORE impl, M3/T031).
Spec: docs/library/design/20260711_wave-3-reconciled-build-spec-rb-8-12-dic_4f427b.md sections RB-9, RB-10.

RB-9  title normalization: NFC+strip at the door (landed with RB-8), read-side bridge for
      pre-RB-9 dirty titles, collision scan surface (flag, never auto-merge).
RB-10 supersede-target validation BEFORE write + all-retired-title detector as a separate
      additive surface.

Contract frozen here:
  AgentMemory.find_normalization_collisions() -> List[dict]   (RB-9 doctor scan)
  SupersedeTargetError(ValueError)                            (RB-10 teaching refusal)
  AgentMemory.get_retired_titles() -> List[dict]              (RB-10 detector)

Run: py -m pytest tests/test_w3_rb9_rb10.py -q
"""
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.foundation.store import DictStore
    from core.learning.agent_memory import (
        AgentMemory, Decision, SupersedeRaceError, SupersedeTargetError, normalize_title,
    )
    _BUILT = hasattr(AgentMemory, "get_retired_titles") and \
        hasattr(AgentMemory, "find_normalization_collisions")
except ImportError:
    _BUILT = False

pytestmark = pytest.mark.skipif(
    not _BUILT, reason="RB-9/RB-10 pins pre-registered; impl pending (assertions frozen)")


@pytest.fixture()
def mem():
    return AgentMemory(store=DictStore())


def _forge(mem, dec_id, title, body, created, superseded=False, supersedes=None):
    d = Decision(id=dec_id, title=title, status="accepted", context="", decision=body,
                 rationale=[], alternatives=[], consequences={"positive": [], "negative": []},
                 created_at=created, session_id="", supersedes=supersedes, superseded=superseded)
    mem.store.hset(mem.KEY_DECISIONS, field=dec_id, value=json.dumps(asdict(d)))
    mem.store.zadd(mem.KEY_DECISION_INDEX,
                   {dec_id: datetime.fromisoformat(created).timestamp()})
    return dec_id


# ---------------- RB-9 ----------------

def test_trailing_space_renote_supersedes_clean_title(mem):
    a = mem.decide_with_retry("where-we-are", "clean")
    b = mem.decide_with_retry("where-we-are  ", "dirty-authored re-note")
    active = [d for d in mem.get_decisions(days=3650)]
    assert [d.id for d in active] == [b], "NFC+strip: one chain, one active"


def test_nfc_equals_nfd(mem):
    import unicodedata
    nfc = "café-status"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd, "sanity: the two encodings differ pre-normalization"
    a = mem.decide_with_retry(nfc, "one")
    b = mem.decide_with_retry(nfd, "two")
    assert len(mem.get_decisions(days=3650)) == 1, "NFC==NFD: same chain"


def test_case_distinct_titles_not_merged(mem):
    a = mem.decide_with_retry("LEXICON-status", "upper")
    b = mem.decide_with_retry("lexicon-status", "lower")
    assert len(mem.get_decisions(days=3650)) == 2, \
        "no case folding: case-distinct titles stay distinct (precision first)"


def test_pre_rb9_dirty_title_found_by_clean_renote(mem):
    # forged legacy record whose STORED title carries a trailing space (pre-RB-9 write)
    _forge(mem, "ADR_0101000001_aaaaaaaa", "old-arc-status ", "legacy dirty",
           datetime(2026, 1, 1).isoformat())
    b = mem.decide_with_retry("old-arc-status", "clean re-note")
    actives = mem.get_decisions(days=3650)
    assert [d.id for d in actives] == [b], \
        "read-side bridge: the clean re-note supersedes the dirty-titled legacy record"


def test_collision_scan_flags_pre_existing_normalization_twins(mem):
    _forge(mem, "ADR_0101000001_aaaaaaaa", "twin-title", "one",
           datetime(2026, 1, 1).isoformat())
    _forge(mem, "ADR_0101000002_bbbbbbbb", "twin-title ", "two",
           datetime(2026, 1, 2).isoformat())
    hits = mem.find_normalization_collisions()
    assert any(normalize_title(h.get("title", "")) == "twin-title" for h in hits), \
        "two actives normalizing equal are FLAGGED"
    assert len(mem.get_decisions(days=3650)) == 2, "flagged, never auto-merged"


# ---------------- RB-10 ----------------

def test_ghost_target_refused_before_write(mem):
    with pytest.raises(SupersedeTargetError):
        mem.decide("t", "body", supersedes="ADR_nonexistent_00000000")
    assert mem.get_decisions(days=3650, include_superseded=True) == [], \
        "refused BEFORE any write: no record, no index entry"


# (Self-supersede is unexpressible by construction -- decide() generates its own id --
#  so no pin exists for it; deepseek's defensive check may still land in impl, unpinned.)


def test_superseded_target_refused_with_head_named(mem):
    a = mem.decide_with_retry("t", "A")
    b = mem.decide_with_retry("t", "B")
    with pytest.raises(SupersedeTargetError) as ei:
        mem.decide("t", "C", supersedes=a)   # a is already superseded by b
    assert b in str(ei.value), "the teaching error names the current head"


def test_all_retired_title_listed_active_title_not(mem):
    a = mem.decide_with_retry("vanished-arc-status", "done")
    mem.retire_decision(a)
    keep = mem.decide_with_retry("live-title", "active")
    gone = mem.get_retired_titles()
    titles = {g.get("title") for g in gone}
    assert "vanished-arc-status" in titles
    assert "live-title" not in titles
