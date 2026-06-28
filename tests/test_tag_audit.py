"""
Tag governance G2 -- mis-tag detection (flag-only).

Bar: flag planted mis-tags; NO false alarms on high-confidence/confirmed; invariant I6
(the scan is byte read-only). Worst-cases: empty, all-confirmed, corrupt beat, the scorer seam.

Isolated: temp FileStore. Run: py -m pytest tests/test_tag_audit.py -q
"""
import json
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.schema import Beat, beat_key
from core.narrative.tagging import TagHistory
from core.narrative.tag_audit import TagAuditor


def _epoch(iso):
    return datetime.fromisoformat(iso).timestamp()


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _put(store, bid, track, conf, at, *, confirmed=False, summary="x"):
    h = TagHistory()
    if confirmed:
        h.add(track, confirmed=True, at=at)
    else:
        h.add(track, confidence=conf, source="manual", at=at)
    b = Beat(id=bid, at=at, kind="note", summary=summary, source="ledger:" + bid,
             track=track, tag_history=h.to_list())
    store.set(beat_key(bid), json.dumps(b.to_dict()))
    store.zadd("narr:beats:timeline", {bid: _epoch(at)})
    store.zadd(f"narr:track:{track}:beats", {bid: _epoch(at)})


def _seq(store):
    _put(store, "b1", "ai-setup", 0.95, "2026-01-01T01:00:00")
    _put(store, "b2", "ai-setup", 0.95, "2026-01-01T02:00:00")
    _put(store, "b3", "stemroller", 0.3, "2026-01-01T03:00:00", summary="ZLUDA build failed")  # planted
    _put(store, "b4", "ai-setup", 0.95, "2026-01-01T04:00:00")
    _put(store, "b5", "research", 0.95, "2026-01-01T05:00:00")


def test_planted_mistag_flagged():
    store = _store(); _seq(store)
    suspects = TagAuditor(store).flag_suspect_tags()
    ids = [s.beat_id for s in suspects]
    assert ids == ["b3"], f"only the planted low-conf lone tag should flag, got {ids}"
    s = suspects[0]
    assert "low_confidence" in s.reasons and any("inconsistent" in r for r in s.reasons)


def test_no_false_alarms_on_high_or_confirmed():
    store = _store()
    _put(store, "h1", "ai-setup", 0.95, "2026-01-01T01:00:00")          # high conf
    _put(store, "h2", "stemroller", 0.3, "2026-01-01T02:00:00", confirmed=True)  # confirmed (even if low/lone)
    _put(store, "h3", "ai-setup", 0.95, "2026-01-01T03:00:00")
    assert TagAuditor(store).flag_suspect_tags() == [], "high-conf + confirmed must never flag"


def test_readonly_invariant_I6():
    store = _store(); _seq(store)
    before = json.dumps(store._data, sort_keys=True)
    TagAuditor(store).flag_suspect_tags()
    after = json.dumps(store._data, sort_keys=True)
    assert before == after, "I6: the scan must be byte-for-byte read-only"


def test_empty_and_corrupt_robustness():
    assert TagAuditor(_store()).flag_suspect_tags() == []     # empty -> no crash
    store = _store()
    _put(store, "ok", "ai-setup", 0.95, "2026-01-01T01:00:00")
    store.set(beat_key("garbage"), "{not valid json")        # corrupt beat -> skipped
    store.zadd("narr:beats:timeline", {"garbage": 999})
    # a beat whose tag_history entry is corrupt -> current() copes, beat still scannable
    bad = Beat(id="bad", at="2026-01-01T02:00:00", kind="note", summary="x", source="l",
               track="vision", tag_history=[{"value": "vision", "confidence": "NaNxx"}])
    store.set(beat_key("bad"), json.dumps(bad.to_dict()))
    store.zadd("narr:beats:timeline", {"bad": _epoch("2026-01-01T02:00:00")})
    out = TagAuditor(store).flag_suspect_tags()              # must not raise
    assert "bad" in [s.beat_id for s in out], "corrupt-history beat -> low confidence -> flagged, not fatal"


def test_scorer_seam_confident_learning():
    store = _store(); _seq(store)
    # an embedding/LLM scorer (Slice 6) confidently says b3 is ai-setup
    def scorer(beat):
        return ("ai-setup", 0.9) if beat.id == "b3" else (None, 0.0)
    suspects = {s.beat_id: s for s in TagAuditor(store).flag_suspect_tags(scorer=scorer)}
    assert any("model_suggests:ai-setup" in r for r in suspects["b3"].reasons)


if __name__ == "__main__":
    for fn in [test_planted_mistag_flagged, test_no_false_alarms_on_high_or_confirmed,
               test_readonly_invariant_I6, test_empty_and_corrupt_robustness,
               test_scorer_seam_confident_learning]:
        fn()
    print("ALL TAG GOVERNANCE G2 TESTS PASSED")
